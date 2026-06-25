from transformers import pipeline
import torch

DEVICE = "cpu"

classifier = pipeline(
    "zero-shot-classification",
    model="valhalla/distilbart-mnli-12-3",
    device=DEVICE
)

TONE_LOOP = [
    "Formal", "Informal", "Optimistic", "Worried", "Friendly", "Curious", "Surprised", "Cooperative", 
    "Confident", "Joyful", "Appreciative", "Neutral", "Direct"
    ]

CONFIDENCE_FLOOR = 0.6

def classify_tone(text: str) -> dict:
    result = classifier(
        text,
        candidate_labels=TONE_LOOP,
        multi_label=True
    )

    scores = dict(zip(result["labels"], result["scores"]))

    # Keep only labels above threshold
    qualifying = [
        {"label": label, "score": score}
        for label, score in zip(result["labels"], result["scores"])
        if score >= CONFIDENCE_FLOOR
    ]

    # Sort descending by score
    qualifying.sort(key=lambda x: x["score"], reverse=True)

    # Top 2
    dominant = qualifying[:2]

    return {
        "dominant_tones": dominant,
        "scores": scores
    }