from spellchecker import SpellChecker

spell = SpellChecker()

def check_word(word: str) -> dict:
    """
    Checks a single word for spelling correctness.
    Returns whether it's correct and a suggested fix if not.
    """
    cleaned = word.strip().lower()

    if not cleaned or not cleaned.isalpha():
        return {"is_correct": True, "suggestion": None}

    if cleaned in spell:
        return {"is_correct": True, "suggestion": None}

    suggestion = spell.correction(cleaned)
    return {"is_correct": False, "suggestion": suggestion}