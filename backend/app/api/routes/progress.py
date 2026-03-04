from fastapi import APIRouter, Header
from app.schemas.progress import QuizAttemptRequest
from app.services.progress_service import get_progress_summary, record_quiz_attempt

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("/summary")
def progress_summary(x_session_id: str = Header(default="demo-user")):
    return get_progress_summary(x_session_id)


@router.post("/quiz-attempt")
def save_quiz_attempt(
    payload: QuizAttemptRequest,
    x_session_id: str = Header(default="demo-user"),
):
    record_quiz_attempt(
        session_id=x_session_id,
        quiz_mode=payload.quiz_mode,
        difficulty=payload.difficulty,
        topic_slugs=payload.topic_slugs,
        total_questions=payload.total_questions,
        correct_answers=payload.correct_answers,
    )
    return {"status": "saved"}