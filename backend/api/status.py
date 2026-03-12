from fastapi import APIRouter
import state

router = APIRouter()


@router.get("/status")
def get_status():
    return {
        "ready": state.is_ready(),
        "filename": state.get_legacy_filename(),
        "chunks_count": state.get_legacy_chunks_count(),
    }
