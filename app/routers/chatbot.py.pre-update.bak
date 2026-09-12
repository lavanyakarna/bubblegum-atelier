from fastapi import APIRouter, HTTPException
from app.schemas import ChatbotRequest, ChatbotResponse
from app.services.chatbot_service import ChatbotService

router = APIRouter(tags=["chatbot"])

_chatbot_service = None


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
def chatbot_reply(payload: ChatbotRequest):
    service = get_chatbot_service()
    return service.get_reply(payload.message)
