"""Hash de senha (scrypt da stdlib, com salt) e JWT."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from . import config

_N, _R, _P = 2 ** 14, 8, 1


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        calc = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt),
                              n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(calc, base64.b64decode(dk))
    except Exception:
        return False


# Usado para gastar o mesmo tempo quando o e-mail não existe (evita enumeração por timing).
DUMMY_HASH = hash_password("senha-fantasma")


def create_access_token(user_id: int, token_version: int) -> tuple[str, int]:
    """O token carrega só identidade e versão. Perfil e departamento vêm SEMPRE do banco."""
    expires = timedelta(minutes=config.ACCESS_TOKEN_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "ver": token_version, "iat": now, "exp": now + expires}
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, config.SECRET_KEY, algorithms=[config.JWT_ALGORITHM],
                      options={"require": ["exp", "sub", "ver"]})
