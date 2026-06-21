from language_tool_python import LanguageTool as lt
from regex import match

def test_language_tool():
    print("Loading LanguageTool... this may take a few moments the first time")
    tool = lt('en-US')
    print("LanguageTool loaded successfully")

    test_sentences = [
        "The cat sat on the mat.",
        "She don't know what to do.",
        "He going to the store yesterday.",
        "The students completed their assignment."
    ]

    for sentence in test_sentences:
        matches = tool.check(sentence)
        print(f"\nSentence: {sentence}")
        if matches:
            print("Grammar issues found:")
            for match in matches:
                print(f"- {match.rule_id}: {match.message} (at position {match.offset}) {match.context} {match.replacements}")
                print(f"  Length: {match.error_length}")
                print(f"  Suggestions: {match.replacements[:3]}")
        else:
            print("No grammar issues found.")

test_language_tool()