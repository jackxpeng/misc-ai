import asyncio
import json
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

# Load environment variables (like GEMINI_API_KEY)
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

# Initialize Gemini Client
ai_client = genai.Client()

# The SSE endpoint automatically exposed by your FastMCP server
SERVER_URL = "http://localhost:8080/sse"

async def run_agent():
    print(f"🔗 Connecting to MCP 2.0 Server at {SERVER_URL}...")
    
    # 1. Establish the "Two-Pipe" connection:
    # streams[0] = Read stream (persistent SSE connection for receiving JSON-RPC messages).
    # streams[1] = Write stream (HTTP POST client for sending messages).
    async with sse_client(SERVER_URL) as streams:
        # 2. ClientSession multiplexes these streams to act like a single bidirectional connection.
        # Calling tools sends a POST via streams[1] and waits for the response on streams[0].
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # --- PHASE 1: DYNAMIC DISCOVERY ---
            # Instead of loading a massive prompt, the agent asks: "What can you do?"
            print("\n🔍 Discovering available tools and resources...")
            tools_response = await session.list_tools()
            resources_response = await session.list_resources()
            
            tools_info = []
            for tool in tools_response.tools:
                print(f"   - Found tool: {tool.name}")
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                })
            
            resources_info = []
            for resource in resources_response.resources:
                print(f"   - Found resource: {resource.uri} ({resource.name})")
                resources_info.append({
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description
                })
            
            # --- PHASE 2: EXECUTION ---
            user_prompt = input("\nWhat would you like to do? (e.g., 'Deploy a 2U server named node-99')\n> ")
            if not user_prompt.strip():
                return
            
            # Pre-fetch telemetry if the prompt mentions a potential target node
            # This demonstrates how the client can proactively gather resource context
            telemetry_context = ""
            if "node-" in user_prompt.lower():
                import re
                node_match = re.search(r"node-\d+", user_prompt.lower())
                if node_match:
                    node_id = node_match.group(0)
                    print(f"📡 Proactively fetching telemetry for {node_id}...")
                    resource_uri = f"rack://{node_id}/telemetry"
                    try:
                        resource_content = await session.read_resource(resource_uri)
                        telemetry_context = f"\nCRITICAL CONTEXT - Current Telemetry for {node_id}:\n{resource_content.contents[0].text}"
                    except Exception as e:
                        print(f"⚠️ Could not fetch telemetry: {e}")

            print("\n🧠 Asking Gemini to pick a tool...")
            
            system_prompt = f"""
            You are an AI assistant that uses tools. Based on the user's request, select the appropriate tool and provide the arguments.
            
            COOPERATIVE AGENT GUIDELINES:
            - Be helpful. If the user's request is clear (e.g., "Deploy a server to node-01") but a specific technical argument like 'server_id' is missing, INFER or GENERATE a reasonable value (e.g., "srv-node-01-001") rather than refusing.
            - The 'server_id' can be a unique string you generate if not provided.
            
            SAFETY MANDATE:
            - ALWAYS evaluate available telemetry before suggesting a deployment.
            - If a rack's temperature is (CRITICAL), REFUSE to deploy new hardware and explain why.
            
            Available Tools:
            {json.dumps(tools_info, indent=2)}
            
            Available Resource Templates:
            {json.dumps(resources_info, indent=2)}
            {telemetry_context}
            
            User Request: {user_prompt}
            
            Respond with a JSON object containing EXACTLY three keys:
            "tool_name": the name of the tool to use (string, or null if refusing/not found)
            "arguments": the arguments for the tool (object)
            "message": A brief explanation of your decision (especially if generating IDs or refusing)
            
            If no tool is appropriate or if you are refusing for safety reasons, "tool_name" must be null.
            """
            
            # Use Gemini to decide what tool to call
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=system_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            if not response or not response.text:
                print("❌ Received empty response from Gemini.")
                return
            
            try:
                decision = json.loads(response.text)
                target_tool = decision.get("tool_name")
                payload = decision.get("arguments", {})
                explanation = decision.get("message", "")
            except Exception as e:
                print(f"❌ Failed to parse LLM response: {response.text}")
                return
            
            if explanation:
                print(f"🤖 AI Reasoning: {explanation}")
                
            if not target_tool:
                if not explanation:
                    print("ℹ️ Gemini decided no tool was appropriate for this request.")
                return
            
            print(f"\n🚀 Executing '{target_tool}' with payload: {payload}")
            
            result = await session.call_tool(target_tool, arguments=payload)
            
            # 3. Handle the response and pass it back to the LLM's context
            if result.isError:
                print(f"❌ Error from server: {result.content}")
            else:
                # result.content is a list of content blocks (text, images, etc.)
                for content in result.content:
                     print(f"✅ Server responded: {content.text}")

if __name__ == "__main__":
    # Run the async event loop
    asyncio.run(run_agent())
