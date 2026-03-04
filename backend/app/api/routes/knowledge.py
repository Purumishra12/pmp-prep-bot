from fastapi import APIRouter, HTTPException
from app.services.document_service import build_index, get_knowledge_status

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/status")
def knowledge_status():
    return get_knowledge_status()


@router.post("/rebuild")
def rebuild_knowledge_index():
    try:
        return build_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))