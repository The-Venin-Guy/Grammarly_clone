from fastapi import APIRouter
from sentence_tracker import reset

router = APIRouter()

@router.post("/reset")
def reset_cache():
    reset()
    return {"status": "cleared"}