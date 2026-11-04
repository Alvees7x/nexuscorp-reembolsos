"""Erros de aplicação com código HTTP e código de erro estáveis."""


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}


def unauthorized(message="Autenticação necessária ou inválida"):
    return AppError(401, "nao_autenticado", message, {"WWW-Authenticate": "Bearer"})


def forbidden(message="Sem permissão para esta operação", code="acesso_negado"):
    return AppError(403, code, message)


def not_found(message="Recurso não encontrado"):
    # Também usado quando o recurso existe mas pertence a outro usuário/departamento,
    # para não revelar a existência (RN02/RN03).
    return AppError(404, "nao_encontrado", message)


def conflict(message, code="conflito"):
    return AppError(409, code, message)


def invalid(message, code="dados_invalidos"):
    return AppError(422, code, message)
