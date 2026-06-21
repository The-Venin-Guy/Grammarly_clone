import spacy
import language_tool_python
import torch
from transformers import pipeline, T5ForConditionalGeneration, T5Tokenizer
from cmudict import dict as cmudict_dict  # Much more accurate syllable counting

print("Loading models...")
# Disable parsing pieces we don't need to speed up spaCy
nlp = spacy.load("en_core_web_sm")

# Dropping the CoLA BERT model to save VRAM/Time unless strictly required
tone_analyzer = pipeline("text-classification", model="bhadresh-savani/distilbert-base-uncased-emotion", device=-1) # set device=0 for GPU
language_tool = language_tool_python.LanguageTool('en-US')

t5_tokenizer = T5Tokenizer.from_pretrained("prithivida/grammar_error_correcter_v1")
t5_model = T5ForConditionalGeneration.from_pretrained("prithivida/grammar_error_correcter_v1")
# Move T5 to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
t5_model = t5_model.to(device)
print("All models ready")

# Accurate syllable fallback dictionary
d = cmudict_dict()
def count_syllables_accurate(word: str) -> int:
    word_clean = word.lower().strip(".,!?;:()\"'")
    if word_clean in d:
        return [len(list(y for y in x if y[-1].isdigit())) for x in d[word_clean]][0]
    # Simple rule fallback if word not in dictionary
    vowels = "aeiouy"
    count = sum(1 for char in word_clean if char in vowels)
    if word_clean.endswith("e"): count -= 1
    return max(1, count)

def process_document_features(doc) -> dict:
    """Extracts passive voice, SVA errors, and syllables in ONE pass over the doc."""
    passive_count = 0
    agreement_errors = []
    total_syllables = 0
    sentences_data = []

    for sent in doc.sents:
        is_passive = False
        for token in sent:
            if token.is_alpha:
                total_syllables += count_syllables_accurate(token.text)

            # Detect Passive Voice
            if token.dep_ == "nsubjpass":
                is_passive = True

            # Subject-Verb Agreement Rules (using absolute doc offsets)
            if token.dep_ in ("nsubj", "nsubjpass") and token.head.pos_ == "VERB":
                subject = token
                verb = token.head

                # Rule 1: Singular noun + Plural verb
                if subject.tag_ in ("NN", "NNP") and verb.tag_ == "VBP":
                    agreement_errors.append({
                        "message": f"'{subject.text}' is singular; requires a singular verb.",
                        "offset": verb.idx, # Absolute document offset
                        "length": len(verb.text),
                        "suggestions": [],
                        "rule": "SPACY_SVA"
                    })
                # Rule 2: Plural noun + Singular verb
                elif subject.tag_ in ("NNS", "NNPS") and verb.tag_ == "VBZ":
                    agreement_errors.append({
                        "message": f"'{subject.text}' is plural; requires a plural verb.",
                        "offset": verb.idx,
                        "length": len(verb.text),
                        "suggestions": [],
                        "rule": "SPACY_SVA"
                    })
                # Rule 3: Pronouns
                elif subject.text.lower() in ("we", "they") and verb.tag_ == "VBZ":
                    agreement_errors.append({
                        "message": f"'{subject.text}' needs a plural verb form.",
                        "offset": verb.idx,
                        "length": len(verb.text),
                        "suggestions": [],
                        "rule": "SPACY_SVA"
                    })

        if is_passive:
            passive_count += 1
            
        sentences_data.append({
            "sentence": sent.text,
            "passive_voice": is_passive
        })

    return {
        "passive_count": passive_count,
        "agreement_errors": agreement_errors,
        "total_syllables": total_syllables,
        "sentences_data": sentences_data
    }

def batch_correct_text(sentences: list) -> str:
    """Batches sentences together to speed up Transformer inference significantly."""
    input_texts = [f"gec: {s}" for s in sentences]
    # Batch encoding
    inputs = t5_tokenizer(input_texts, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
    
    with torch.no_grad():
        outputs = t5_model.generate(**inputs, max_length=128, num_beams=3, early_stopping=True)
    
    corrected_sentences = t5_tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return " ".join(corrected_sentences)

def analyze_text(text: str) -> dict:
    if not text.strip():
        return {"error": "Empty text provided"}

    # Pass text through spaCy ONCE
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    num_sentences = len(sentences)
    num_words = len([t for t in doc if t.is_alpha])

    if num_sentences == 0 or num_words == 0:
        return {"error": "Invalid text structural processing"}

    # Heuristics pass
    doc_features = process_document_features(doc)

    # Calculate Readability (Flesch Reading Ease)
    avg_sentence_length = num_words / num_sentences
    avg_syllables = doc_features["total_syllables"] / num_words
    readability_score = round(206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables), 1)
    readability_score = max(0, min(100, readability_score))

    # LanguageTool execution
    lt_matches = language_tool.check(text)
    errors = []
    seen_offsets = set()

    for match in lt_matches:
        errors.append({
            "message": match.message,
            "offset": match.offset,
            "length": match.error_length,
            "suggestions": match.replacements[:3],
            "rule": match.rule_id
        })
        seen_offsets.add(match.offset)

    # Blend spaCy errors keeping accurate offsets intact
    for error in doc_features["agreement_errors"]:
        if error["offset"] not in seen_offsets:
            errors.append(error)

    # ML Inference tasks (Batched T5 + Tone)
    corrected_text = batch_correct_text(sentences)
    tone_result = tone_analyzer(text[:512])[0]

    return {
        "sentences": doc_features["sentences_data"],
        "total_errors": len(errors),
        "errors": errors,
        "corrected_text": corrected_text,
        "tone": tone_result['label'],
        "readability_score": readability_score,
        "passive_voice_count": doc_features["passive_count"]
    }