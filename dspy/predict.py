import os
import dspy
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# 1. Configure your execution engine (the LM)
lm = dspy.LM("gemini/gemini-2.5-flash", api_key=os.environ.get("GEMINI_API_KEY"))
dspy.configure(lm=lm)

# 2. Define the Interface (The Signature)
# We declare exactly what goes in and what must come out, with strong typing.
class ExtractInfo(dspy.Signature):
    """Extract structured information from text."""
    
    text: str = dspy.InputField()
    
    title: str = dspy.OutputField()
    headings: list[str] = dspy.OutputField()
    entities: list[dict[str, str]] = dspy.OutputField(desc="a list of entities and their metadata")

# 3. Assign an Execution Strategy (The Module)
# dspy.Predict simply executes the signature directly. 
# If we wanted step-by-step reasoning, we could swap this out for dspy.ChainOfThought(ExtractInfo) 
# without changing the signature at all.
extractor = dspy.Predict(ExtractInfo)

# 4. Execute
payload = """
Apple Inc. announced its latest iPhone 14 today. 
The CEO, Tim Cook, highlighted its new features in a press release.
"""

response = extractor(text=payload)

print("Title:", response.title)
print("Entities:", response.entities)
