from pydantic import BaseModel
from typing import Optional

class ErrorDetail(BaseModel):
    message: str
    offset: int
    length: int
    replacements: list[str]
    rule_id: str

class SentenceResult(BaseModel):
    id: int
    original_text: str
    corrected_text: Optional[str] = None
    formality_score: Optional[float] = None
    tone_rewrite: Optional[str] = None
    passive_rewrite: Optional[str] = None
    clarity_rewrite: Optional[str] = None
    has_error: bool
    errors: list[ErrorDetail]
    passive_voice: bool
    hash: str
    analyzed: bool
    modified: bool

class ReadabilityResult(BaseModel):
    flesch_reading_ease: float
    grade_level: float
    readability_label: str

class DocumentStats(BaseModel):
    total_sentences: int
    sentences_reanalyzed: int
    sentences_cached: int
    passive_voice_count: int

class AnalyzeResponse(BaseModel):
    sentences: list[SentenceResult]
    readability: ReadabilityResult
    document_stats: DocumentStats

class SpellCheckResponse(BaseModel):
    is_correct: bool
    suggestion: str | None