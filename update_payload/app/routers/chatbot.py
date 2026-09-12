from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

from app.schemas import ChatbotRequest, ChatbotResponse
from app.services.chatbot_service import ChatbotService
from app.storage import append_event, read_json, write_json

router = APIRouter(tags=["chatbot"])

_chatbot_service = None
MAX_STORED_CHATS = 200


def get_chatbot_service():
    global _chatbot_service
    if _chatbot_service is None:
        try:
            _chatbot_service = ChatbotService()
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="Chatbot model not trained yet. Run: python -m app.services.chatbot_service",
            )
    return _chatbot_service


@router.post("/chatbot", response_model=ChatbotResponse)
def chatbot_reply(payload: ChatbotRequest, x_customer_id: str = Header(default="anonymous")):
    service = get_chatbot_service()
    result = service.get_reply(payload.message)

    # remember the conversation so the owner dashboard can show real chats
    chats = read_json("chats.json", [])
    if not isinstance(chats, list):
        chats = []
    chats.append({
        "message": payload.message,
        "reply": result.get("reply"),
        "intent": result.get("intent"),
        "method": result.get("method"),
        "customer": x_customer_id,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    write_json("chats.json", chats[-MAX_STORED_CHATS:])

    append_event({
        "customer_id": x_customer_id,
        "type": "chat",
        "product_id": None,
        "meta": {"intent": result.get("intent"), "method": result.get("method")},
    })

    return result
