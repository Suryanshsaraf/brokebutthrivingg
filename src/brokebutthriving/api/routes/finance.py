from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from brokebutthriving.core.database import get_session
from brokebutthriving.models.entities import CashflowEntry, DailyCheckIn, ExpenseEntry, Participant
from brokebutthriving.schemas.api import (
    CashflowEntryCreate,
    CashflowEntryRead,
    DailyCheckInCreate,
    DailyCheckInRead,
    DashboardSummary,
    ExpenseBatchCreate,
    ExpenseEntryCreate,
    ExpenseEntryRead,
    SimulationRequest,
    SimulationResponse,
)
from brokebutthriving.services.analytics import build_dashboard, simulate_plan


router = APIRouter(prefix="/participants/{participant_id}", tags=["finance"])


def _ensure_participant(session: Session, participant_id: str) -> Participant:
    participant = session.get(Participant, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return participant


@router.post("/expenses", response_model=ExpenseEntryRead, status_code=status.HTTP_201_CREATED)
def create_expense(
    participant_id: str,
    payload: ExpenseEntryCreate,
    session: Session = Depends(get_session),
) -> ExpenseEntry:
    _ensure_participant(session, participant_id)
    expense = ExpenseEntry(participant_id=participant_id, **payload.model_dump())
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


@router.post("/expenses/batch", response_model=list[ExpenseEntryRead], status_code=status.HTTP_201_CREATED)
def create_expense_batch(
    participant_id: str,
    payload: ExpenseBatchCreate,
    session: Session = Depends(get_session),
) -> list[ExpenseEntry]:
    _ensure_participant(session, participant_id)
    expenses = [ExpenseEntry(participant_id=participant_id, **entry.model_dump()) for entry in payload.expenses]
    session.add_all(expenses)
    session.commit()
    for expense in expenses:
        session.refresh(expense)
    return expenses


@router.post("/cashflows", response_model=CashflowEntryRead, status_code=status.HTTP_201_CREATED)
def create_cashflow(
    participant_id: str,
    payload: CashflowEntryCreate,
    session: Session = Depends(get_session),
) -> CashflowEntry:
    _ensure_participant(session, participant_id)
    cashflow = CashflowEntry(participant_id=participant_id, **payload.model_dump())
    session.add(cashflow)
    session.commit()
    session.refresh(cashflow)
    return cashflow


@router.post("/checkins", response_model=DailyCheckInRead, status_code=status.HTTP_201_CREATED)
def create_checkin(
    participant_id: str,
    payload: DailyCheckInCreate,
    session: Session = Depends(get_session),
) -> DailyCheckIn:
    _ensure_participant(session, participant_id)
    checkin = DailyCheckIn(participant_id=participant_id, **payload.model_dump())
    session.add(checkin)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Check-in already exists for this day") from exc

    session.refresh(checkin)
    return checkin


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    participant_id: str, session: Session = Depends(get_session)
) -> DashboardSummary:
    try:
        return build_dashboard(session, participant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/simulate", response_model=SimulationResponse)
def run_simulation(
    participant_id: str,
    payload: SimulationRequest,
    session: Session = Depends(get_session),
) -> SimulationResponse:
    try:
        return simulate_plan(session, participant_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/expenses", response_model=list[ExpenseEntryRead])
def list_expenses(participant_id: str, session: Session = Depends(get_session)) -> list[ExpenseEntry]:
    _ensure_participant(session, participant_id)
    return session.exec(
        select(ExpenseEntry)
        .where(ExpenseEntry.participant_id == participant_id)
        .order_by(ExpenseEntry.occurred_at.desc())
    ).all()


@router.get("/cashflows", response_model=list[CashflowEntryRead])
def list_cashflows(
    participant_id: str, session: Session = Depends(get_session)
) -> list[CashflowEntry]:
    _ensure_participant(session, participant_id)
    return session.exec(
        select(CashflowEntry)
        .where(CashflowEntry.participant_id == participant_id)
        .order_by(CashflowEntry.occurred_at.desc())
    ).all()

