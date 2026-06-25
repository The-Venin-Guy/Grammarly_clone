from fastapi import APIRouter
from schemas.request import AnalyzeToneRequest
from schemas.response import AnalyzeToneResponse
from tone_label import classify_tone

router = APIRouter()

@router.post("/analyze-tone", response_model=AnalyzeToneResponse)
def analyze_tone_route(request: AnalyzeToneRequest):
    result = classify_tone(request.text)
    return AnalyzeToneResponse(**result)