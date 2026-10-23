from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.services.ask import AskService

router = APIRouter(prefix="/api/ask", tags=["ask"])


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


@router.post("")
def ask_macrolens(request: AskRequest):
    return AskService().ask(request.question.strip())


@router.post("/plan")
def plan_macrolens(request: AskRequest):
    service = AskService()
    return {"question": request.question.strip(), "research_plan": service.planner.plan(request.question).to_dict()}
