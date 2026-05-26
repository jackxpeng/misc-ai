import dspy
import os
from dotenv import load_dotenv, find_dotenv
from dspy.teleprompt import BootstrapFewShot

load_dotenv(find_dotenv())

lm = dspy.LM("gemini/gemini-2.5-flash", api_key=os.environ.get("GEMINI_API_KEY"))
dspy.configure(lm=lm)

# 1. The Interface
class ClassifyBug(dspy.Signature):
    """Classify if a bug is a UI issue or a Backend issue."""
    bug_description: str = dspy.InputField()
    category: str = dspy.OutputField(desc="UI or Backend")

# 2. The Unoptimized Module (Notice we use ChainOfThought)
bug_classifier = dspy.ChainOfThought(ClassifyBug)

# 3. Training Data (Inputs + Expected Outputs)
# Notice we do NOT write out the reasoning steps. We only provide the final answer.
trainset = [
    dspy.Example(bug_description="The submit button is overlapping the text field.", category="UI").with_inputs("bug_description"),
    dspy.Example(bug_description="Database connection timeout when saving user profile.", category="Backend").with_inputs("bug_description"),
    dspy.Example(bug_description="The text is rendering off-screen on mobile.", category="UI").with_inputs("bug_description"),
]

# 4. The Metric (How do we grade if the model succeeded during training?)
def exact_match_metric(example, pred, trace=None):
    return example.category.strip().lower() == pred.category.strip().lower()

# 5. The Optimizer (The Compiler)
print("Compiling... (DSPy is figuring out the reasoning steps automatically)")
optimizer = BootstrapFewShot(metric=exact_match_metric, max_bootstrapped_demos=2, max_labeled_demos=1)

# This compiles our high-level logic into an optimized state
compiled_classifier = optimizer.compile(bug_classifier, trainset=trainset)

# 6. Execute the compiled system on a brand new bug
test_bug = "Outbox pattern relay fails to publish to the message broker due to missing credentials."
response = compiled_classifier(bug_description=test_bug)

print("\n--- COMPILED OUTPUT ---")
print(f"Category: {response.category}")

print("\n--- THE MAGIC: WHAT DSPY ACTUALLY SENT TO GEMINI ---")
# This prints the final prompt DSPy constructed under the hood
lm.inspect_history(n=1)