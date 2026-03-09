from fastapi import APIRouter
import state

router = APIRouter()


@router.get("/status")
def get_status():
    return {
        "ready": state.is_ready(),
        "filename": state.current_filename,
        "chunks_count": state.chunks_count,
    }
