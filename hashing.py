import hashlib

def hash_sentence(sentence: str) -> str:
    """
    Returns a SHA-256 hash of the sentence text.
    Used to detect whether a sentence has changed between requests.
    """
    return hashlib.sha256(sentence.strip().encode("utf-8")).hexdigest()