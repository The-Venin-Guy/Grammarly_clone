import language_tool_python
from grammar_model import correct
import spacy

nlp = spacy.load("en_core_web_sm")

SHORT_WORD_WHITELIST = {
    "a", "i", "an", "to", "of", "in", "on", "at", "by", "is", "it", "as",
    "be", "or", "if", "so", "we", "he", "me", "my", "no", "up", "do", "go",
    "us", "am", "ok"
}

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

    lt_has_error = len(matches) > ERROR_THRESHOLD
    corrected = None
    has_error = False

    if lt_has_error or needs_extra_check(sentence):
        candidate = await correct(sentence)
        if candidate.strip() != sentence.strip():
            corrected = candidate
            has_error = True

    return {"original": sentence, "corrected": corrected, "has_error": has_error, "errors": errors}

def check_only(sentence: str) -> list[dict]:
    """
    Runs only LanguageTool, no Ollama call. Used for fast inline
    highlighting before the full (slower) analysis pipeline runs.
    """
    matches = tool.check(sentence)
    return [
        {
            "message": m.message,
            "offset": m.offset,
            "length": m.error_length,
            "replacements": m.replacements[:3],
            "rule_id": m.rule_id
        }
        for m in matches
    ]

def has_suspicious_short_token(sentence: str) -> bool:
    """
    Flags any 1-2 letter alphabetic token not in a whitelist of
    legitimate short English words. Catches typos like "o" for "of".
    """
    doc = nlp(sentence)
    for token in doc:
        if token.is_alpha and len(token.text) <= 2:
            if token.text.lower() not in SHORT_WORD_WHITELIST:
                return True
    return False

def has_missing_determiner(sentence: str) -> bool:
    """
    Flags a singular common noun with no determiner attached.
    Catches phrasing like "type of thing" missing "a".
    """
    doc = nlp(sentence)
    for token in doc:
        if token.tag_ == "NN":
            has_det = any(child.dep_ == "det" for child in token.children)
            if not has_det:
                return True
    return False

def needs_extra_check(sentence: str) -> bool:
    return has_suspicious_short_token(sentence) or has_missing_determiner(sentence)