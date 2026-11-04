import enum


class Role(str, enum.Enum):
    EMPLOYEE = "colaborador"
    MANAGER = "gestor"
    FINANCE = "financeiro"


class Category(str, enum.Enum):
    FOOD = "alimentacao"
    TRANSPORT = "transporte"
    LODGING = "hospedagem"
    MATERIALS = "materiais"


class Status(str, enum.Enum):
    DRAFT = "rascunho"
    AWAITING_MANAGER = "aguardando_gestor"
    AWAITING_FINANCE = "aguardando_financeiro"
    APPROVED = "aprovada"
    PAID = "paga"
    REJECTED = "recusada"


class Stage(str, enum.Enum):
    EMPLOYEE = "colaborador"
    MANAGER = "gestor"
    FINANCE = "financeiro"


class Decision(str, enum.Enum):
    SUBMITTED = "enviada"
    APPROVED = "aprovada"
    REJECTED = "recusada"
    PAID = "paga"
