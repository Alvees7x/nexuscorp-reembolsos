"""Máquina de estados do ciclo de vida da solicitação (seção 6 do enunciado).

É um módulo puro (sem banco/HTTP): toda transição passa por `next_status`, então
transições incompatíveis são impossíveis em qualquer ponto da aplicação.
"""
import enum

from .enums import Status


class Action(str, enum.Enum):
    SUBMIT = "submit"
    MANAGER_APPROVE = "manager_approve"
    MANAGER_REJECT = "manager_reject"
    FINANCE_APPROVE = "finance_approve"
    FINANCE_REJECT = "finance_reject"
    PAY = "pay"


class InvalidTransition(Exception):
    pass


TRANSITIONS: dict[tuple[Status, Action], Status] = {
    (Status.DRAFT, Action.SUBMIT): Status.AWAITING_MANAGER,
    (Status.AWAITING_MANAGER, Action.MANAGER_APPROVE): Status.AWAITING_FINANCE,   # RN08
    (Status.AWAITING_MANAGER, Action.MANAGER_REJECT): Status.REJECTED,
    (Status.AWAITING_FINANCE, Action.FINANCE_APPROVE): Status.APPROVED,
    (Status.AWAITING_FINANCE, Action.FINANCE_REJECT): Status.REJECTED,
    (Status.APPROVED, Action.PAY): Status.PAID,                                  # RN10
}

TERMINAL = frozenset({Status.PAID, Status.REJECTED})


def next_status(current: Status, action: Action) -> Status:
    try:
        return TRANSITIONS[(current, action)]
    except KeyError:
        raise InvalidTransition(f"{action.value} não é permitida em '{current.value}'")


def can_edit(status: Status) -> bool:
    """RN07: só rascunhos podem ser editados/excluídos."""
    return status == Status.DRAFT
