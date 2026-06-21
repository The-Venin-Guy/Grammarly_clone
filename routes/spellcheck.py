from fastapi import APIRouter
from schemas.request import SpellCheckRequest
from schemas.response import SpellCheckResponse
from spellcheck_service import check_word

router = APIRouter()

@router.post("/spellcheck", response_model=SpellCheckResponse)
def spellcheck_word(request: SpellCheckRequest):
    result = check_word(request.word)
    return SpellCheckResponse(**result)