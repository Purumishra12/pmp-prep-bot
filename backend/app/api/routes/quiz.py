import json
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException

from app.core.topic_map import get_flat_topics, get_topic_by_slug
from app.schemas.quiz import QuizGenerateRequest, QuizGenerateResponse, QuizQuestion
from app.services.document_service import search_relevant_chunks
from app.services.ollama_service import generate_with_ollama

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


def _normalize_chunk(chunk: Dict[str, Any]) -> Dict[str, str]:
    source = (
        chunk.get("source")
        or chunk.get("document")
        or chunk.get("file_name")
        or chunk.get("filename")
        or chunk.get("pdf_name")
        or "Unknown Source"
    )

    page = (
        chunk.get("page")
        or chunk.get("page_number")
        or chunk.get("page_num")
        or chunk.get("page_index")
        or "N/A"
    )

    text = (
        chunk.get("text")
        or chunk.get("content")
        or chunk.get("chunk_text")
        or chunk.get("snippet")
        or ""
    )

    return {
        "source": str(source),
        "page": str(page),
        "text": str(text).strip(),
    }


def _strip_json_fence(raw: str) -> str:
    raw = raw.strip()

    if raw.startswith("```json"):
        raw = raw[len("```json"):].strip()
    elif raw.startswith("```"):
        raw = raw[len("```"):].strip()

    if raw.endswith("```"):
        raw = raw[:-3].strip()

    return raw


def _extract_json_object(raw: str) -> str:
    raw = _strip_json_fence(raw)

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No valid JSON object found in model output.")

    return raw[start:end + 1]


def _normalize_correct_answer(correct_answer: str, options: List[str]) -> str:
    if not correct_answer:
        raise ValueError("correct_answer is missing.")

    answer = str(correct_answer).strip().upper()

    if answer in {"A", "B", "C", "D"}:
        return answer

    # If model returns "A. Something" or full option text
    for idx, opt in enumerate(options):
        letter = chr(65 + idx)
        option_text = str(opt).strip()

        if answer == option_text.upper():
            return letter

        if answer.startswith(f"{letter}.") or answer.startswith(f"{letter})"):
            return letter

    raise ValueError(f"Could not normalize correct_answer: {correct_answer}")


def _parse_quiz_json(raw_output: str, requested_count: int) -> List[QuizQuestion]:
    json_text = _extract_json_object(raw_output)

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON. {str(e)}")

    questions = parsed.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("JSON does not contain a valid 'questions' list.")

    cleaned_questions: List[QuizQuestion] = []

    for q in questions:
        if not isinstance(q, dict):
            continue

        question = str(q.get("question", "")).strip()
        options = q.get("options", [])
        explanation = str(q.get("explanation", "")).strip()
        correct_answer = q.get("correct_answer", "")

        if not question:
            continue

        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"Each question must have exactly 4 options. Got: {options}")

        options = [str(opt).strip() for opt in options]
        normalized_answer = _normalize_correct_answer(str(correct_answer), options)

        cleaned_questions.append(
            QuizQuestion(
                question=question,
                options=options,
                correct_answer=normalized_answer,
                explanation=explanation or "No explanation provided.",
            )
        )

    if not cleaned_questions:
        raise ValueError("No valid quiz questions could be parsed from model output.")

    return cleaned_questions[:requested_count]


def _get_quizable_topics() -> List[Dict[str, Any]]:
    # User asked to exclude Exam Strategy from quiz generation
    return [
        topic
        for topic in get_flat_topics()
        if topic.get("domain") != "exam-strategy"
    ]


def _resolve_selected_topics(payload: QuizGenerateRequest) -> List[Dict[str, Any]]:
    quiz_mode = payload.quiz_mode
    quizable_topics = _get_quizable_topics()
    quizable_by_slug = {t["slug"]: t for t in quizable_topics}

    if quiz_mode == "single-topic":
        if not payload.topic_slug:
            raise HTTPException(status_code=422, detail="topic_slug is required for single-topic mode.")

        topic = quizable_by_slug.get(payload.topic_slug)
        if not topic:
            raise HTTPException(status_code=404, detail=f"Quiz topic not found or not allowed: {payload.topic_slug}")

        return [topic]

    if quiz_mode == "multi-topic":
        if not payload.topic_slugs or not isinstance(payload.topic_slugs, list):
            raise HTTPException(status_code=422, detail="topic_slugs is required for multi-topic mode.")

        unique_slugs = []
        seen = set()
        for slug in payload.topic_slugs:
            if slug and slug not in seen:
                seen.add(slug)
                unique_slugs.append(slug)

        selected = [quizable_by_slug[slug] for slug in unique_slugs if slug in quizable_by_slug]

        if not selected:
            raise HTTPException(status_code=404, detail="No valid quiz topics found for multi-topic mode.")

        return selected

    if quiz_mode == "mock-test":
        if not quizable_topics:
            raise HTTPException(status_code=404, detail="No quiz topics available for mock-test mode.")
        return quizable_topics

    raise HTTPException(status_code=422, detail=f"Unsupported quiz_mode: {quiz_mode}")


def _search_chunks_for_topics(selected_topics: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    all_chunks: List[Dict[str, str]] = []
    seen = set()

    per_topic_k = 4
    if len(selected_topics) >= 4:
        per_topic_k = 2
    elif len(selected_topics) == 3:
        per_topic_k = 3

    for topic in selected_topics:
        topic_name = topic.get("name", "")
        keywords = " ".join(topic.get("keywords", []))
        query = f"{topic_name}. {keywords}".strip()

        try:
            raw_chunks = search_relevant_chunks(query, top_k=per_topic_k)
        except TypeError:
            # fallback if your function only accepts one parameter
            raw_chunks = search_relevant_chunks(query)

        for chunk in raw_chunks:
            normalized = _normalize_chunk(chunk)
            key = (normalized["source"], normalized["page"], normalized["text"][:120])

            if normalized["text"] and key not in seen:
                seen.add(key)
                all_chunks.append(normalized)

    return all_chunks[:12]


def _build_quiz_prompt(
    quiz_mode: str,
    selected_topics: List[Dict[str, Any]],
    difficulty: str,
    num_questions: int,
    context_chunks: List[Dict[str, str]],
) -> str:
    topic_names = [t["name"] for t in selected_topics]
    topic_slugs = [t["slug"] for t in selected_topics]

    context_text = "\n\n".join(
        [
            f"[Source: {c.get('source', 'Unknown Source')} | Page: {c.get('page', 'N/A')}]\n{c.get('text', '')}"
            for c in context_chunks
        ]
    )

    if not context_text.strip():
        context_text = "No indexed context found. Use PMP-standard knowledge carefully."

    mode_instruction = ""
    if quiz_mode == "single-topic":
        mode_instruction = (
            "Generate all questions strictly from the single selected topic only."
        )
    elif quiz_mode == "multi-topic":
        mode_instruction = (
            "Generate a balanced mixed quiz using ONLY the selected topics. "
            "Distribute questions across those topics as evenly as possible."
        )
    elif quiz_mode == "mock-test":
        mode_instruction = (
            "Generate a realistic PMP-style mixed mock test using a broad mix of allowed PMP topics. "
            "Do NOT use Exam Strategy topics."
        )

    return f"""
You are a PMP exam prep assistant.

Generate exactly {num_questions} multiple-choice PMP-style questions.

Quiz mode: {quiz_mode}
Difficulty: {difficulty}
Selected topic slugs: {topic_slugs}
Selected topic names: {topic_names}

Rules:
1. {mode_instruction}
2. Each question must have exactly 4 answer options.
3. Options must be strings in this format:
   "A. ..."
   "B. ..."
   "C. ..."
   "D. ..."
4. correct_answer must be ONLY one letter: A or B or C or D
5. explanation must be concise but clear.
6. Return ONLY valid JSON.
7. Do NOT wrap the response in markdown or code fences.
8. Prefer scenario-based PMP wording.
9. Use the knowledge context below when relevant.

Knowledge context:
{context_text}

Return JSON in exactly this format:
{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "A. Option A",
        "B. Option B",
        "C. Option C",
        "D. Option D"
      ],
      "correct_answer": "A",
      "explanation": "Why A is correct."
    }}
  ]
}}
""".strip()


@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz(
    payload: QuizGenerateRequest,
    x_session_id: str = Header(default="demo-user"),
):
    print("=== /api/quiz/generate called ===")
    print("x_session_id:", x_session_id)
    print("quiz_mode:", payload.quiz_mode)
    print("topic_slug:", payload.topic_slug)
    print("topic_slugs:", payload.topic_slugs)
    print("difficulty:", payload.difficulty)
    print("num_questions:", payload.num_questions)

    selected_topics = _resolve_selected_topics(payload)
    selected_topic_slugs = [t["slug"] for t in selected_topics]

    context_chunks = _search_chunks_for_topics(selected_topics)
    print("Retrieved chunks:", len(context_chunks))

    prompt = _build_quiz_prompt(
        quiz_mode=payload.quiz_mode,
        selected_topics=selected_topics,
        difficulty=payload.difficulty,
        num_questions=payload.num_questions,
        context_chunks=context_chunks,
    )

    raw_output = generate_with_ollama(prompt)
    print("Raw Ollama quiz output:")
    print(raw_output[:3000])

    try:
        parsed_questions = _parse_quiz_json(raw_output, payload.num_questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse quiz JSON: {str(e)}")

    return QuizGenerateResponse(
        quiz_mode=payload.quiz_mode,
        topic_slug=payload.topic_slug if payload.quiz_mode == "single-topic" else None,
        topic_slugs=selected_topic_slugs,
        difficulty=payload.difficulty,
        questions=parsed_questions,
    )