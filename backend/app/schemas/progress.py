from typing import List, Literal
from pydantic import BaseModel, Field


class QuizAttemptRequest(BaseModel):
    quiz_mode: Literal["single", "multi", "mock"]
    difficulty: str
    topic_slugs: List[str]
    total_questions: int = Field(ge=1)
    correct_answers: int = Field(ge=0)