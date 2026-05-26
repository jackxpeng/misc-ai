import os
import dspy
import argparse
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

def main():
    parser = argparse.ArgumentParser(description="Extract information from text using DSPy.")
    parser.add_argument(
        "--cot", 
        action="store_true", 
        help="Use Chain of Thought reasoning instead of a simple prediction."
    )
    args = parser.parse_args()

    # 1. Configure your execution engine (the LM)
    lm = dspy.LM("gemini/gemini-2.5-flash", api_key=os.environ.get("GEMINI_API_KEY"))
    dspy.configure(lm=lm)

    # 2. Define the Interface (The Signature)
    class ExtractInfo(dspy.Signature):
        """Extract structured information from text."""
        
        text: str = dspy.InputField()
        
        title: str = dspy.OutputField()
        headings: list[str] = dspy.OutputField()
        entities: list[dict[str, str]] = dspy.OutputField(desc="a list of entities and their metadata")

    # 3. Assign an Execution Strategy (The Module)
    if args.cot:
        print("Running with Chain of Thought reasoning...\n")
        extractor = dspy.ChainOfThought(ExtractInfo)
    else:
        print("Running with simple prediction...\n")
        extractor = dspy.Predict(ExtractInfo)

    # 4. Execute
    payload = """
    Apple Inc. announced its latest iPhone 14 today. 
    The CEO, Tim Cook, highlighted its new features in a press release.
    """

    response = extractor(text=payload)

    print("Title:", response.title)
    if args.cot:
        print("Reasoning:", response.reasoning)
    print("Entities:", response.entities)

if __name__ == "__main__":
    main()
