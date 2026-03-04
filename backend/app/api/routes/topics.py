from fastapi import APIRouter, HTTPException
from app.core.topic_map import get_all_topics, get_flat_topics, get_topic_by_slug

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("")
def list_topics():
    return {"domains": get_all_topics()}


@router.get("/flat")
def list_flat_topics():
    return {"topics": get_flat_topics()}


@router.get("/{slug}")
def get_topic(slug: str):
    topic = get_topic_by_slug(slug)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic