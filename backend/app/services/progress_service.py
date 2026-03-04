import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PROGRESS_FILE = DATA_DIR / "progress.json"


def _ensure_store():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"sessions": {}}, f, indent=2)


def _load() -> Dict[str, Any]:
    _ensure_store()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: Dict[str, Any]):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _get_session(data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    sessions = data.setdefault("sessions", {})
    if session_id not in sessions:
        sessions[session_id] = {
            "explanations": [],
            "quiz_attempts": []
        }
    return sessions[session_id]


def record_explanation(session_id: str, topic_slug: str):
    data = _load()
    session = _get_session(data, session_id)
    session["explanations"].append(
        {
            "topic_slug": topic_slug,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    _save(data)


def record_quiz_attempt(
    session_id: str,
    quiz_mode: str,
    difficulty: str,
    topic_slugs: List[str],
    total_questions: int,
    correct_answers: int,
):
    data = _load()
    session = _get_session(data, session_id)
    session["quiz_attempts"].append(
        {
            "quiz_mode": quiz_mode,
            "difficulty": difficulty,
            "topic_slugs": topic_slugs,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    _save(data)


def get_progress_summary(session_id: str) -> Dict[str, Any]:
    data = _load()
    session = _get_session(data, session_id)

    explanations = session["explanations"]
    quiz_attempts = session["quiz_attempts"]

    total_quizzes = len(quiz_attempts)
    total_questions = sum(a["total_questions"] for a in quiz_attempts)
    total_correct = sum(a["correct_answers"] for a in quiz_attempts)

    accuracy = 0.0
    if total_questions > 0:
        accuracy = round((total_correct / total_questions) * 100, 2)

    topic_stats: Dict[str, Dict[str, Any]] = {}

    for item in explanations:
        slug = item["topic_slug"]
        topic_stats.setdefault(
            slug,
            {"topic_slug": slug, "explanations": 0, "quiz_questions": 0, "correct_answers": 0}
        )
        topic_stats[slug]["explanations"] += 1

    for attempt in quiz_attempts:
        slugs = attempt["topic_slugs"] or []
        for slug in slugs:
            topic_stats.setdefault(
                slug,
                {"topic_slug": slug, "explanations": 0, "quiz_questions": 0, "correct_answers": 0}
            )
            topic_stats[slug]["quiz_questions"] += attempt["total_questions"]
            topic_stats[slug]["correct_answers"] += attempt["correct_answers"]

    return {
        "session_id": session_id,
        "total_explanations": len(explanations),
        "total_quiz_attempts": total_quizzes,
        "total_questions_answered": total_questions,
        "total_correct_answers": total_correct,
        "accuracy_percent": accuracy,
        "topic_stats": list(topic_stats.values()),
        "recent_quiz_attempts": quiz_attempts[-10:][::-1],
    }