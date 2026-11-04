from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import require_roles
from ..enums import Category, Role, Status
from ..models import User
from ..schemas import ExpenseOut, RejectIn, ReviewIn

router = APIRouter(prefix="/manager/expenses", tags=["Gestor"])
manager_only = require_roles(Role.MANAGER)


@router.get("", response_model=list[ExpenseOut], summary="Solicitações do MEU departamento")
def list_department(department_id: int | None = None, status: Status | None = None,
                    category: Category | None = None,
                    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                    manager: User = Depends(manager_only), db: Session = Depends(get_db)):
    return services.list_for_manager(db, manager, department_id, status, category, limit, offset)


@router.post("/{expense_id}/approve", response_model=ExpenseOut, summary="Gestor aprova")
def approve(expense_id: int, body: ReviewIn | None = None, manager: User = Depends(manager_only),
            db: Session = Depends(get_db)):
    return services.manager_decide(db, manager, expense_id, True, body.comment if body else None)


@router.post("/{expense_id}/reject", response_model=ExpenseOut, summary="Gestor recusa (justificativa obrigatória)")
def reject(expense_id: int, body: RejectIn, manager: User = Depends(manager_only),
           db: Session = Depends(get_db)):
    return services.manager_decide(db, manager, expense_id, False, body.comment)
