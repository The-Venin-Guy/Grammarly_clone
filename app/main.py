from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Note: Standard naming convention update
from pydantic import BaseModel
# Import the optimized analysis function and the batch correction function
from app.pipeline import analyze_text, batch_correct_text, nlp

app = FastAPI(title="Grammar and Writing Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextInput(BaseModel):
    text: str

@app.get("/")
def root():
    return {"status": "Grammar checker is running"}

@app.post("/check")
def check(input_data: TextInput):
    text = input_data.text.strip()
    
    # Matching the exact dictionary structure returned by the optimized analyze_text
    if not text:
        return {
            "sentences": [],
            "total_errors": 0,
            "errors": [],
            "corrected_text": "",
            "tone": "N/A",
            "readability_score": 0.0,
            "passive_voice_count": 0
        }
        
    return analyze_text(text)

@app.post("/correct")
def correct(input_data: TextInput):
    text = input_data.text.strip()
    if not text:
        return {"corrected_text": ""}
    
    # Leverage spaCy to break text into clean sentences for the batch transformer
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    
    corrected_text = batch_correct_text(sentences)
    return {"corrected_text": corrected_text}