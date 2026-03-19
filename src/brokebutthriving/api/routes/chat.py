from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from brokebutthriving.core.database import get_session
from brokebutthriving.models.entities import Participant
from brokebutthriving.schemas.api import ChatRequest, ChatResponse
from brokebutthriving.services.agent import run_agent

router = APIRouter(tags=["chat"])


@router.post(
    "/participants/{participant_id}/chat",
    response_model=ChatResponse,
)
def chat_with_copilot(
    participant_id: str,
    payload: ChatRequest,
    session: Session = Depends(get_session),
) -> ChatResponse:
    """Send a message to the AI copilot and get a data-grounded response."""
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")

    try:
        reply, tools_used = run_agent(
            session=session,
            participant_id=participant_id,
            message=payload.message,
            history=payload.history,
            category_budgets=payload.category_budgets,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI copilot error: {exc}",
        ) from exc

    return ChatResponse(reply=reply, tools_used=tools_used)
