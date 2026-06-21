from hashing import hash_sentence

# In-memory cache: { hash: analysis_result_dict }
_cache: dict[str, dict] = {}

def check_sentence(sentence: str) -> tuple[str, dict | None]:
    """
    Hashes a sentence and checks if it has a cached result.

    Returns:
        (hash, cached_result_or_None)
        - If the sentence was seen before, cached_result is the stored dict.
        - If new/changed, cached_result is None — caller must analyze and call store().
    """
    h = hash_sentence(sentence)
    return h, _cache.get(h)

def store(h: str, result: dict) -> None:
    """
    Saves the analysis result for a given hash, so future identical
    sentences can skip reanalysis.
    """
    _cache[h] = result

def reset() -> None:
    """
    Clears all stored sentence hashes. Called by POST /reset.
    """
    _cache.clear()