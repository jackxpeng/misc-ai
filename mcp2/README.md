# MCP 2.0 Project

This project demonstrates the Model Context Protocol (MCP) using a FastMCP server and a Gemini-powered client.

## The "Two-Pipe" Architecture

In MCP 2.0 over Server-Sent Events (SSE), the transport layer uses a dual-channel system.

When the client executes this line:

```python
async with sse_client(SERVER_URL) as streams:
```

The `sse_client` context manager isn't just opening one connection. It returns multiple streams (`streams`), doing two specific things:

1. **Pipe 1 (The Read Stream - `streams[0]`)**: It opens the long-lived, one-way Server-Sent Events connection. This stays open permanently, waiting for the server to push JSON-RPC messages down to the client.
2. **Pipe 2 (The Write Stream - `streams[1]`)**: When the SSE connection is first established, the FastMCP server sends down a special URL endpoint specifically for receiving messages. The SDK takes this URL and configures a standard asynchronous HTTP client (the write stream).

### What Happens During Execution?

When both pipes are passed into the `ClientSession`:

```python
async with ClientSession(streams[0], streams[1]) as session:
```

The `ClientSession` object acts as a multiplexer. It hides the asymmetry of the network, so it feels exactly like using a WebSocket.

Here is what actually happens on the network when interacting with the server:

- **`await session.list_tools()`**: The session takes the request, formats it as JSON-RPC, and uses **Pipe 2** to fire off a standard HTTP POST request to the server. It does *not* open a new SSE connection. The server receives the POST, processes it, and streams the answer back down **Pipe 1** (the open SSE connection).
- **`await session.call_tool(...)`**: Works exactly the same way. The session fires another distinct HTTP POST request over **Pipe 2**. The server executes the logic (e.g., deploying bare metal), and then pushes the result back down **Pipe 1**.

### Why build it this way?

If you were writing this in raw C++ or Rust without an SDK, you would have to manage a listening thread for the SSE stream and a separate HTTP client for the POSTs, manually mapping the JSON-RPC request IDs to the corresponding responses.

The Python MCP SDK abstracts that complexity away so developers can just write `await session.call_tool()` and let the library handle the asynchronous routing of the POST requests and the SSE reads. Every action makes a new POST request under the hood, but the `ClientSession` does the heavy lifting to tie it all together!

## MCP vs. gRPC: Architecture for AI

While both are RPC frameworks, they optimize for different goals: **gRPC** for machine-to-machine speed, and **MCP** for AI-to-machine discoverability.

| Feature | gRPC (Mental Model) | MCP 2.0 (AI Model) |
| :--- | :--- | :--- |
| **Serialization** | **Protobuf (Binary)**: Compact and fast. Requires ahead-of-time compilation. | **JSON (Text)**: Native to LLMs. Agents can read schemas and generate arguments effortlessly. |
| **Schema** | **Static**: Hardcoded in `.proto` files. Changes require client/server recompilation. | **Dynamic**: Negotiated at runtime. Server broadcasts available tools via JSON Schema. |
| **Transport** | **HTTP/2**: Multiplexed binary frames over a persistent TCP connection. | **SSE + HTTP POST**: Dual-channel architecture for upstream and downstream. |
| **Connectivity** | Requires strict HTTP/2 support; can be difficult to route through proxies. | Standard HTTP/1.1 or 2; easily pierces corporate firewalls and load balancers. |

### The Strategic Trade-off
- **Use gRPC** for internal microservices where throughput and low latency are the primary metrics.
- **Use MCP** for building LLM agent control planes. It trades minor parsing overhead for **runtime discovery**, allowing agents to learn and reason about new tools dynamically without needing client-side updates.