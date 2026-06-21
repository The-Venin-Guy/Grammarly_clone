from fastapi import APIRouter
from schemas.request import GrammarCheckRequest
from schemas.response import GrammarCheckResponse, ErrorDetail
from grammar_service import check_only

router = APIRouter()

@router.post("/grammar-check", response_model=GrammarCheckResponse)
def grammar_check(request: GrammarCheckRequest):
    errors = check_only(request.text)
    return GrammarCheckResponse(errors=[ErrorDetail(**e) for e in errors])