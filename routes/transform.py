from fastapi import APIRouter
from schemas.request import TransformRequest
from schemas.response import TransformResponse
from transform_service import transform_text

router = APIRouter()

@router.post("/transform", response_model=TransformResponse)
async def transform_route(request: TransformRequest):
    result = await transform_text(request.text, request.mode)
    return TransformResponse(transformed_text=result)