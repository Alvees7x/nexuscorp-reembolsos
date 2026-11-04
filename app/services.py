"""Regras de negócio. Todas as verificações acontecem ANTES de qualquer escrita,
então uma operação não autorizada nunca altera o banco."""
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .enums import Category, Decision, Role, Stage, Status
from .errors import conflict, forbidden, invalid, not_found
from .models import ExpenseRequest, ReviewHistory, User, utcnow
from .workflow import Action, InvalidTransition, can_edit, next_status

FINANCE_VISIBLE = (Status.AWAITING_FINANCE, Status.APPROVED, Status.PAID)


# ---------------------------------------------------------------- consultas
def _query():
    return select(ExpenseRequest).options(
        joinedload(ExpenseRequest.requester).joinedload(User.department))


def _fetch(db: Session, expense_id: int) -> ExpenseRequest | None:
    return db.scalars(_query().where(ExpenseRequest.id == expense_id)).first()


def _fetch_own(db: Session, user: User, expense_id: int) -> ExpenseRequest:
    e = _fetch(db, expense_id)
    if e is None or e.requester_id != user.id:  # RN02: 404, sem revelar existência
        raise not_found("Solicitação não encontrada")
    return e


def _reached_finance(e: ExpenseRequest) -> bool:
    if e.status in FINANCE_VISIBLE:
        return True
    return e.status == Status.REJECTED and any(h.stage == Stage.FINANCE for h in e.history)


def can_view(user: User, e: ExpenseRequest) -> bool:
    if e.requester_id == user.id:
        return True
    if user.role == Role.MANAGER:   # RN03: só o próprio departamento, e nunca rascunhos alheios
        return e.requester.department_id == user.department_id and e.status != Status.DRAFT
    if user.role == Role.FINANCE:   # só o que já foi encaminhado pelos gestores
        return _reached_finance(e)
    return False


def get_visible(db: Session, user: User, expense_id: int) -> ExpenseRequest:
    e = _fetch(db, expense_id)
    if e is None or not can_view(user, e):
        raise not_found("Solicitação não encontrada")
    return e


def _paginate(q, status, category, limit, offset):
    if status is not None:
        q = q.where(ExpenseRequest.status == status)
    if category is not None:
        q = q.where(ExpenseRequest.category == category)
    q = q.order_by(ExpenseRequest.created_at.desc(), ExpenseRequest.id.desc())
    return q.limit(limit).offset(offset)


def list_own(db, user, status, category, limit, offset):
    q = _query().where(ExpenseRequest.requester_id == user.id)
    return db.scalars(_paginate(q, status, category, limit, offset)).all()


def list_for_manager(db, manager, department_id, status, category, limit, offset):
    if department_id is not None and department_id != manager.department_id:
        raise forbidden("Gestor só pode consultar o próprio departamento")  # cenário 07
    q = (_query()
         .where(ExpenseRequest.requester.has(User.department_id == manager.department_id))
         .where(ExpenseRequest.status != Status.DRAFT))
    return db.scalars(_paginate(q, status, category, limit, offset)).all()


def list_for_finance(db, department_id, status, category, limit, offset):
    q = _query().where(
        (ExpenseRequest.status.in_(FINANCE_VISIBLE))
        | ((ExpenseRequest.status == Status.REJECTED)
           & ExpenseRequest.history.any(ReviewHistory.stage == Stage.FINANCE)))
    if department_id is not None:
        q = q.where(ExpenseRequest.requester.has(User.department_id == department_id))
    return db.scalars(_paginate(q, status, category, limit, offset)).all()


def get_history(db: Session, user: User, expense_id: int):
    e = get_visible(db, user, expense_id)
    return db.scalars(select(ReviewHistory).options(joinedload(ReviewHistory.reviewer))
                      .where(ReviewHistory.expense_id == e.id)
                      .order_by(ReviewHistory.created_at, ReviewHistory.id)).all()


# ---------------------------------------------------------------- colaborador
def _commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("Violação de integridade dos dados")


def _ensure_unique_receipt(db, user_id, receipt_ref, exclude_id=None):
    q = select(ExpenseRequest.id).where(ExpenseRequest.requester_id == user_id,
                                        ExpenseRequest.receipt_ref == receipt_ref)
    if exclude_id is not None:
        q = q.where(ExpenseRequest.id != exclude_id)
    if db.scalar(q) is not None:  # RN05
        raise conflict("Já existe uma despesa sua com esta referência de comprovante",
                       "comprovante_duplicado")


def create_expense(db, user, data):
    _ensure_unique_receipt(db, user.id, data.receipt_ref)
    e = ExpenseRequest(requester_id=user.id, status=Status.DRAFT, **data.model_dump())
    db.add(e)
    _commit(db)
    return _fetch(db, e.id)


def update_expense(db, user, expense_id, data):
    e = _fetch_own(db, user, expense_id)
    if not can_edit(e.status):  # RN07 / cenário 06
        raise conflict("A solicitação não pode mais ser alterada", "solicitacao_nao_editavel")
    changes = data.model_dump(exclude_unset=True)
    if "receipt_ref" in changes:
        _ensure_unique_receipt(db, user.id, changes["receipt_ref"], exclude_id=e.id)
    for k, v in changes.items():
        setattr(e, k, v)
    e.updated_at = utcnow()
    _commit(db)
    return _fetch(db, e.id)


def delete_expense(db, user, expense_id):
    e = _fetch_own(db, user, expense_id)
    if not can_edit(e.status):
        raise conflict("A solicitação não pode mais ser excluída", "solicitacao_nao_editavel")
    db.delete(e)
    _commit(db)


# ---------------------------------------------------------------- transições
def _transition(db, e, actor, action, stage, decision, comment=None):
    try:
        new_status = next_status(e.status, action)
    except InvalidTransition:
        raise conflict("Operação incompatível com a situação atual da solicitação",
                       "transicao_invalida")
    now = utcnow()
    # UPDATE condicional: se outra requisição mudou o status no meio tempo, não escreve.
    res = db.execute(update(ExpenseRequest)
                     .where(ExpenseRequest.id == e.id, ExpenseRequest.status == e.status)
                     .values(status=new_status, updated_at=now)
                     .execution_options(synchronize_session=False))
    if res.rowcount != 1:
        db.rollback()
        raise conflict("A solicitação foi alterada por outra operação", "transicao_invalida")
    db.add(ReviewHistory(expense_id=e.id, reviewer_id=actor.id, stage=stage,
                         decision=decision, comment=comment, created_at=now))  # RN12
    _commit(db)
    db.refresh(e)
    return e


def submit_expense(db, user, expense_id):
    e = _fetch_own(db, user, expense_id)
    return _transition(db, e, user, Action.SUBMIT, Stage.EMPLOYEE, Decision.SUBMITTED)


def manager_decide(db, manager, expense_id, approve: bool, comment):
    e = _fetch(db, expense_id)
    if (e is None or e.requester.department_id != manager.department_id  # RN03 / cenário 02
            or e.status == Status.DRAFT):
        raise not_found("Solicitação não encontrada")
    if e.requester_id == manager.id:  # RN09
        raise forbidden("Ninguém pode analisar uma solicitação de sua própria autoria",
                        "segregacao_de_funcoes")
    if not approve and not comment:   # RN11
        raise invalid("Recusa exige justificativa")
    action = Action.MANAGER_APPROVE if approve else Action.MANAGER_REJECT
    decision = Decision.APPROVED if approve else Decision.REJECTED
    return _transition(db, e, manager, action, Stage.MANAGER, decision, comment)


def finance_decide(db, finance, expense_id, action: Action, comment=None):
    e = _fetch(db, expense_id)
    if e is None or e.status == Status.DRAFT:  # rascunho é privado do solicitante
        raise not_found("Solicitação não encontrada")
    if e.requester_id == finance.id:           # RN09
        raise forbidden("Ninguém pode analisar uma solicitação de sua própria autoria",
                        "segregacao_de_funcoes")
    if action == Action.FINANCE_REJECT and not comment:  # RN11
        raise invalid("Recusa exige justificativa")
    decision = {Action.FINANCE_APPROVE: Decision.APPROVED,
                Action.FINANCE_REJECT: Decision.REJECTED,
                Action.PAY: Decision.PAID}[action]
    # RN08/RN10/cenário 05: a máquina de estados barra "fora de sequência" (409).
    return _transition(db, e, finance, action, Stage.FINANCE, decision, comment)
