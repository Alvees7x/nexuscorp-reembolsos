import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .enums import Role
from .errors import forbidden, unauthorized
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False, description="Token obtido em POST /auth/login")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    """RN01 e RN14. Perfil/departamento são lidos do banco a cada requisição."""
    if creds is None:
        raise unauthorized()
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise unauthorized("Token inválido ou expirado")
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.token_version != payload["ver"]:
        raise unauthorized("Token inválido ou expirado")
    return user


def require_roles(*roles: Role):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden("Seu perfil não tem permissão para esta operação")
        return user
    return checker
