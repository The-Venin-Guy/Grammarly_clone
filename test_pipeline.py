import gradio as gr
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

MODEL_NAME = "luis-account/formality_classification_model"
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def predict_formality(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
    score = outputs.logits.item()
    return f"Formality Score: {score:.2f}"

interface = gr.Interface(
    fn=predict_formality,
    inputs=gr.Textbox(lines=2, placeholder="Enter a sentence...", label="Input Sentence"),
    outputs=gr.Textbox(label="Formality Score"),
    title="Formality Scorer",
    description="Enter a sentence and see its predicted formality percentage (-3 = very informal, 3 = very formal)."
)

if __name__ == "__main__":
    interface.launch()