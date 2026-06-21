import asyncio
import spacy
from tone_model import detect_formality, rewrite_formality, rewrite_active, rewrite_clarity

nlp = spacy.load("en_core_web_sm")

def detect_passive(sentence: str) -> bool:
    doc = nlp(sentence)
    return any(tok.dep_ == "nsubjpass" for tok in doc)

async def analyze(sentence: str, flesch_score: float) -> dict:
    result = {"tone_rewrite": None, "passive_rewrite": None, "clarity_rewrite": None,
              "formality_score": None, "passive_voice": False}

    score = detect_formality(sentence)
    result["formality_score"] = score
    is_passive = detect_passive(sentence)
    result["passive_voice"] = is_passive

    tasks = {}
    if score < 0.2:
        tasks["tone_rewrite"] = rewrite_formality(sentence)
    if is_passive:
        tasks["passive_rewrite"] = rewrite_active(sentence)
    if flesch_score < 50:
        tasks["clarity_rewrite"] = rewrite_clarity(sentence)

    if tasks:
        outcomes = await asyncio.gather(*tasks.values())
        for key, value in zip(tasks.keys(), outcomes):
            result[key] = value

    return result