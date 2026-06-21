from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    text: str

class SpellCheckRequest(BaseModel):
    word: str

class GrammarCheckRequest(BaseModel):
    text: str