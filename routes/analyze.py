import asyncio
import spacy
from fastapi import APIRouter
from schemas.request import AnalyzeRequest
from schemas.response import AnalyzeResponse, SentenceResult, ReadabilityResult, DocumentStats, ErrorDetail
from sentence_tracker import check_sentence, store
from grammar_service import analyze as analyze_grammar
from tone_service import analyze as analyze_tone
from readability import analyze as analyze_readability, get_flesch
from tone_label import classify_tone, is_tone_shift

router = APIRouter()
nlp = spacy.load("en_core_web_sm")


async def process_sentence(sentence: str, flesch_score: float):
    """
    Handles one sentence end-to-end: cache check, or full analysis if new/changed.
    Returns (hash, data_dict, modified_bool).
    """
    h, cached = check_sentence(sentence)

    if cached:
        return h, cached, False

    grammar_result, tone_result = await asyncio.gather(
        analyze_grammar(sentence),
        analyze_tone(sentence, flesch_score)
    )

    tone_spectrum = classify_tone(sentence)

    data = {
        "original_text": sentence,
        "corrected_text": grammar_result["corrected"],
        "has_error": grammar_result["has_error"],
        "errors": grammar_result["errors"],
        "formality_score": tone_result["formality_score"],
        "tone_rewrite": tone_result["tone_rewrite"],
        "passive_rewrite": tone_result["passive_rewrite"],
        "clarity_rewrite": tone_result["clarity_rewrite"],
        "passive_voice": tone_result["passive_voice"],
        "top_tones": tone_spectrum["top_two"],
        "top_tone_index": tone_spectrum["top_index"],
    }
    store(h, data)
    return h, data, True


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    text = request.text
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]
    flesch_score = get_flesch(text)

    # Run every sentence concurrently, not one-by-one
    results = await asyncio.gather(*[
        process_sentence(sentence, flesch_score) for sentence in sentences
    ])

    baseline = classify_tone(text)
    baseline_index = baseline["top_index"]

    sentence_results = []
    reanalyzed = 0
    cached_count = 0
    passive_count = 0

    for idx, (h, data, modified) in enumerate(results, start=1):
        if modified:
            reanalyzed += 1
        else:
            cached_count += 1

        if data["passive_voice"]:
            passive_count += 1

        sentence_tone_index = data.get("top_tone_index")
        tone_shift = (
            sentence_tone_index is not None and is_tone_shift(sentence_tone_index, baseline_index)
        )

        errors_list = [ErrorDetail(**e) for e in data["errors"]]
        data_no_errors = {k: v for k, v in data.items() if k != "errors"}

        sentence_results.append(SentenceResult(
            id=idx, hash=h, analyzed=True, modified=modified,
            errors=errors_list, tone_shift=tone_shift, **data_no_errors
        ))

    readability = analyze_readability(text)

    return AnalyzeResponse(
        sentences=sentence_results,
        readability=ReadabilityResult(**readability),
        document_stats=DocumentStats(
            total_sentences=len(sentences),
            sentences_reanalyzed=reanalyzed,
            sentences_cached=cached_count,
            passive_voice_count=passive_count,
            document_tone=baseline["top_two"]
        ),
        
    )