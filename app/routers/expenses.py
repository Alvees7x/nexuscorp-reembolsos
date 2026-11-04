from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import services
from ..database import get_db
from ..deps import get_current_user
from ..enums import Category, Status
from ..models import User
from ..schemas import ExpenseCreate, ExpenseOut, ExpenseUpdate, HistoryOut

router = APIRouter(prefix="/expenses", tags=["Solicitações (próprias do usuário)"])


@router.post("", response_model=ExpenseOut, status_code=201, summary="Registra solicitação (rascunho)")
def create(data: ExpenseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.create_expense(db, user, data)


@router.get("", response_model=list[ExpenseOut], summary="Lista as MINHAS solicitações")
def list_mine(status: Status | None = None, category: Category | None = None,
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.list_own(db, user, status, category, limit, offset)


@router.get("/{expense_id}", response_model=ExpenseOut,
            summary="Detalhe (dono, gestor do departamento ou financeiro, conforme visibilidade)")
def detail(expense_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.get_visible(db, user, expense_id)


@router.get("/{expense_id}/history", response_model=list[HistoryOut], summary="Histórico de decisões")
def history(expense_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.get_history(db, user, expense_id)


@router.patch("/{expense_id}", response_model=ExpenseOut, summary="Edita (somente em rascunho)")
def update(expense_id: int, data: ExpenseUpdate, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return services.update_expense(db, user, expense_id, data)


@router.delete("/{expense_id}", status_code=204, summary="Exclui (somente em rascunho)")
def delete(expense_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    services.delete_expense(db, user, expense_id)
    return Response(status_code=204)


@router.post("/{expense_id}/submit", response_model=ExpenseOut, summary="Envia para o gestor")
def submit(expense_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return services.submit_expense(db, user, expense_id)
