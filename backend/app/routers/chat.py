from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatMessage, ChatMessageIn, Conversation, ConversationCreate
from app.services import chat as service

router = APIRouter(prefix="/chat", tags=["chat"])

# 로그인 없는 해커톤용 소유권: 브라우저가 만든 임의 UUID를 X-Client-Id 헤더로 보낸다
ClientId = Header(alias="X-Client-Id", min_length=8, max_length=64)


@router.post("/conversations", response_model=Conversation, status_code=201)
def create_conversation(body: ConversationCreate, client_id: str = ClientId) -> Conversation:
    return service.create_conversation(client_id, body.title)


@router.get("/conversations", response_model=list[Conversation])
def list_conversations(client_id: str = ClientId) -> list[Conversation]:
    return service.list_conversations(client_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessage])
def list_messages(conversation_id: str, client_id: str = ClientId) -> list[ChatMessage]:
    return service.list_messages(conversation_id, client_id)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str, body: ChatMessageIn, client_id: str = ClientId
) -> StreamingResponse:
    stream = await service.send_message(conversation_id, client_id, body.content)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
