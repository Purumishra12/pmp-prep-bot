from typing import List, Literal, Optional
from pydantic import BaseModel, Field


QuizMode = Literal["single-topic", "multi-topic", "mock-test"]
DifficultyLevel = Literal["beginner", "intermediate", "exam"]


class QuizGenerateRequest(BaseModel):
    quiz_mode: QuizMode = "single-topic"
    topic_slug: Optional[str] = None
    topic_slugs: Optional[List[str]] = None
    difficulty: DifficultyLevel = "exam"
    num_questions: int = Field(default=3, ge=1, le=10)


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizGenerateResponse(BaseModel):
    quiz_mode: QuizMode
    topic_slug: Optional[str] = None
    topic_slugs: List[str]
    difficulty: DifficultyLevel
    questions: List[QuizQuestion]


class QuizAttemptRequest(BaseModel):
    quiz_mode: str
    difficulty: str
    topic_slugs: List[str]
    total_questions: int
    correct_answers: int