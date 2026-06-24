from transformers import pipeline
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

classifier = pipeline(
    "zero-shot-classification",
    model="valhalla/distilbart-mnli-12-3",
    device=DEVICE
)

# Hand-curated circular ordering, by perceived similarity — same principle
# as Plutchik's Wheel of Emotions. Not derived from any formula; a designed
# sequence, same as a color wheel.
TONE_LOOP = [
    "Formal", "Appreciative", "Optimistic", "Empathetic", "Casual",
    "Confident", "Direct", "Disapproving", "Worried", "Urgent"
]

SHIFT_THRESHOLD = 2  # starting point — needs tuning against real sentences, like every other threshold in this project

def classify_tone(text: str) -> dict:
    result = classifier(text, candidate_labels=TONE_LOOP, multi_label=True)
    top_label = result["labels"][0]
    top_score = result["scores"][0]

    top_two = [label for label, score in zip(result["labels"], result["scores"]) if score > 0.5]
    
    if top_score < 0.5:  # starting guess — needs testing against real sentences, same as every other threshold here
        return {"top_two": [], "top_index": None}

    return {
        "top_two": top_two[:2],  # return at most two labels
        "top_index": TONE_LOOP.index(top_label),
    }

def tone_distance(a_idx: int, b_idx: int) -> int:
    n = len(TONE_LOOP)
    diff = abs(a_idx - b_idx)
    return min(diff, n - diff)

def is_tone_shift(sentence_top_index: int, baseline_index: int) -> bool:
    return tone_distance(sentence_top_index, baseline_index) > SHIFT_THRESHOLD