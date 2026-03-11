import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from rag.prompt import tender_prompt
import state

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


@router.post("/chat")
async def chat(request: ChatRequest):
    if not state.is_ready():
        raise HTTPException(
            status_code=400, detail="Сначала загрузите тендерный документ"
        )

    vs = state.get_vectorstore()
    docs = vs.similarity_search(request.question, k=4)

    context = "\n".join(
        doc.page_content if hasattr(doc, "page_content") else str(doc) for doc in docs
    )

    prompt = tender_prompt.format(context=context, question=request.question)

    async def generate():
        llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)
        async for chunk in llm.astream(prompt):
            if chunk.content:
                yield f"data: {json.dumps({'token': chunk.content})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
