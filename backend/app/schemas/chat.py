from typing import List
from pydantic import BaseModel


class ExplainRequest(BaseModel):
    topic_slug: str
    question: str


class ExplainResponse(BaseModel):
    topic_slug: str
    question: str
    answer: str
    sources: List[str] = []