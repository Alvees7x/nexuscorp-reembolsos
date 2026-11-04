from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import require_roles
from ..enums import Category, Role, Status
from ..models import User
from ..schemas import ExpenseOut, RejectIn, ReviewIn
from ..workflow import Action

router = APIRouter(prefix="/finance/expenses", tags=["Financeiro"])
finance_only = require_roles(Role.FINANCE)


@router.get("", response_model=list[ExpenseOut], summary="Solicitações encaminhadas pelos gestores")
def list_forwarded(department_id: int | None = None, status: Status | None = None,
                   category: Category | None = None,
                   limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   finance: User = Depends(finance_only), db: Session = Depends(get_db)):
    return services.list_for_finance(db, department_id, status, category, limit, offset)


@router.post("/{expense_id}/approve", response_model=ExpenseOut, summary="Financeiro aprova")
def approve(expense_id: int, body: ReviewIn | None = None, finance: User = Depends(finance_only),
            db: Session = Depends(get_db)):
    return services.finance_decide(db, finance, expense_id, Action.FINANCE_APPROVE,
                                   body.comment if body else None)


@router.post("/{expense_id}/reject", response_model=ExpenseOut, summary="Financeiro recusa (justificativa obrigatória)")
def reject(expense_id: int, body: RejectIn, finance: User = Depends(finance_only),
           db: Session = Depends(get_db)):
    return services.finance_decide(db, finance, expense_id, Action.FINANCE_REJECT, body.comment)


@router.post("/{expense_id}/pay", response_model=ExpenseOut, summary="Registra o pagamento")
def pay(expense_id: int, body: ReviewIn | None = None, finance: User = Depends(finance_only),
        db: Session = Depends(get_db)):
    return services.finance_decide(db, finance, expense_id, Action.PAY,
                                   body.comment if body else None)
