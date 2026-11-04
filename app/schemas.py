"""Contratos de entrada e saída.

Todos os modelos de ENTRADA usam extra="forbid": qualquer campo não previsto
(role, department_id, status, requester_id...) é rejeitado com 422, o que impede
elevação de privilégio e "mass assignment" (RN15, cenários 04 e 06).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from .enums import Category, Decision, Role, Stage, Status

EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=EMAIL_RE)]
Justification = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=1000)]
Receipt = Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=100)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
RejectComment = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]
Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]  # RN04


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _not_future(v: date | None):
    if v is not None and v > date.today():  # RN06
        raise ValueError("A data da despesa não pode ser futura")
    return v


# ---------- Autenticação / usuários ----------
class LoginIn(Strict):
    email: Email
    password: str = Field(min_length=1, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RegisterIn(Strict):
    name: Name
    email: Email
    password: str = Field(min_length=8, max_length=128)
    department_id: int


class UserUpdateIn(Strict):
    """Atualização comum: apenas o nome. Perfil e departamento NÃO são aceitos (RN15)."""
    name: Name


class DepartmentOut(ORM):
    id: int
    name: str


class UserSummary(ORM):
    id: int
    name: str
    department: DepartmentOut


class UserOut(UserSummary):
    email: str
    role: Role
    # Sem password_hash por construção: o campo não existe no contrato (RN13).


class ReviewerOut(ORM):
    id: int
    name: str
    role: Role


# ---------- Solicitações ----------
class ExpenseCreate(Strict):
    category: Category
    amount: Money
    expense_date: date
    justification: Justification
    receipt_ref: Receipt

    _check_date = field_validator("expense_date")(_not_future)


class ExpenseUpdate(Strict):
    category: Category | None = None
    amount: Money | None = None
    expense_date: date | None = None
    justification: Justification | None = None
    receipt_ref: Receipt | None = None

    _check_date = field_validator("expense_date")(_not_future)

    @model_validator(mode="after")
    def _validate_fields(self):
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar")
        for f in self.model_fields_set:
            if getattr(self, f) is None:
                raise ValueError(f"O campo '{f}' não pode ser nulo")
        return self


class ExpenseOut(ORM):
    id: int
    requester: UserSummary
    category: Category
    amount: Decimal
    expense_date: date
    justification: str
    receipt_ref: str
    status: Status
    created_at: datetime
    updated_at: datetime


class ReviewIn(Strict):
    comment: Comment | None = None


class RejectIn(Strict):
    comment: RejectComment  # RN11: justificativa obrigatória


class HistoryOut(ORM):
    id: int
    stage: Stage
    decision: Decision
    reviewer: ReviewerOut
    comment: str | None
    created_at: datetime
