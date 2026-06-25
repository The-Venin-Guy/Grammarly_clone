from pydantic import BaseModel
from typing import Literal

class AnalyzeRequest(BaseModel):
    text: str

class SpellCheckRequest(BaseModel):
    word: str

class GrammarCheckRequest(BaseModel):
    text: str

class AnalyzeToneRequest(BaseModel):
    text: str

class TransformRequest(BaseModel):
    text: str
    mode: Literal["Academic", "Professional", "Concise", "Friendly", "Persuasive"]