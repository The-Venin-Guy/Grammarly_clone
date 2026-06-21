from grammar_model import ollama_generate
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_name = "s-nlp/roberta-base-formality-ranker"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name).to(DEVICE)

def detect_formality(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1)
    return probs[0][1].item()

async def rewrite_formality(text):
    prompt = (
        "Rewrite the following sentence in formal English. "
        "Preserve the exact meaning and all factual details — do not change who did what. "
        "Make the smallest change necessary to sound formal. "
        "Return only the rewritten sentence with no explanation:\n\n"
        f"{text}"
    )
    return (await ollama_generate(prompt)).strip()

async def rewrite_active(text):
    prompt = (
        "Rewrite the sentence in active voice. "
        "Keep every pronoun attached to the exact same person it originally referred to — "
        "do not swap 'my' for 'his', or 'her' for 'their', or any other pronoun substitution. "
        "Example:\n"
        "Original: Because of my tiredness, the cake was eaten by him.\n"
        "Rewritten: He ate the cake because of my tiredness.\n\n"
        "Now rewrite this sentence the same way. "
        "Return only the rewritten sentence with no explanation:\n\n"
        f"{text}"
    )
    return (await ollama_generate(prompt)).strip()

async def rewrite_clarity(text):
    prompt = (
        "Simplify the following sentence to make it clearer and easier to read. "
        "Preserve the original meaning and all factual details exactly. "
        "Make the smallest change necessary for clarity. "
        "Return only the simplified sentence with no explanation:\n\n"
        f"{text}"
    )
    return (await ollama_generate(prompt)).strip()