from fastapi import APIRouter, Header, HTTPException

from app.schemas.chat import ExplainRequest, ExplainResponse
from app.core.topic_map import get_topic_by_slug
from app.services.ollama_service import generate_with_ollama
from app.services.document_service import get_knowledge_snippets

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/explain", response_model=ExplainResponse)
def explain_topic(
    payload: ExplainRequest,
    x_session_id: str = Header(default="demo-user")
):
    topic = get_topic_by_slug(payload.topic_slug)

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    snippets = get_knowledge_snippets(payload.question, top_k=3)

    sources = []
    context_blocks = []

    for item in snippets:
        source_name = item.get("source_file", "unknown")
        excerpt = item.get("text", "").strip()

        if excerpt:
            excerpt = excerpt[:1200]
            context_blocks.append(f"Source: {source_name}\nExcerpt:\n{excerpt}")
            sources.append(source_name)

    knowledge_context = "\n\n---\n\n".join(context_blocks) if context_blocks else "No supporting document snippets found."

    prompt = f"""
You are a PMP exam preparation tutor.

Use the provided source excerpts to answer the user's question.
Focus on PMP exam relevance and explain clearly.

Topic:
{topic["name"]}

Topic description:
{topic["description"]}

User question:
{payload.question}

Supporting source excerpts:
{knowledge_context}

Instructions:
- Explain in simple but professional language.
- Stay focused on PMP exam relevance.
- Mention common exam traps if relevant.
- Give an example if helpful.
- Structure the answer with short headings or bullets.
- Use the source excerpts where relevant, but do not quote excessively.
- If the sources are limited, still provide the best PMP-focused explanation.
"""

    try:
        answer = generate_with_ollama(prompt, timeout=300)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    unique_sources = list(dict.fromkeys(sources))

    return ExplainResponse(
        topic_slug=payload.topic_slug,
        question=payload.question,
        answer=answer,
        sources=unique_sources
    )