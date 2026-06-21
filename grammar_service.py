import language_tool_python
from grammar_model import correct

tool = language_tool_python.LanguageTool("en-US")
print("[grammar_service] LanguageTool ready.")

ERROR_THRESHOLD = 0

async def analyze(sentence: str) -> dict:
    matches = tool.check(sentence)
    errors = [
        {"message": m.message, "offset": m.offset, "length": m.error_length,
         "replacements": m.replacements[:3], "rule_id": m.rule_id}
        for m in matches
    ]
    has_error = len(matches) > ERROR_THRESHOLD
    corrected = await correct(sentence) if has_error else None
    return {"original": sentence, "corrected": corrected, "has_error": has_error, "errors": errors}