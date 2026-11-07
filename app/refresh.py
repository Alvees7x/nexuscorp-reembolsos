"""Emissão, rotação e revogação de refresh tokens.

Fluxo:  login -> (access JWT curto + refresh opaco, família nova)
        /auth/refresh -> troca o refresh por um novo da MESMA família (o antigo vira 'usado')
        refresh JÁ USADO apresentado de novo => roubo presumido => revoga a família inteira.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from . import models as _models
from . import config
from .errors import AppError, unauthorized
from .models import User, utcnow

RefreshToken: Any = getattr(_models, "RefreshToken")
from .security import create_access_token

_MSG = "Refresh token inválido ou expirado"


def hash_token(raw: str) -> str:
    # SHA-256 basta: o token tem 384 bits de entropia (scrypt é para senhas humanas).
    return hashlib.sha256(raw.encode()).hexdigest()


def issue(db: Session, user: User, family_id: str | None = None,
          family_expires_at: datetime | None = None) -> tuple[str, int]:
    """Cria um refresh token (sem commit). Devolve (token_em_claro, expira_em_segundos).
    O token em claro só existe aqui e na resposta HTTP; nunca é gravado."""
    now = utcnow()
    family_id = family_id or str(uuid.uuid4())
    family_expires_at = family_expires_at or now + timedelta(days=config.REFRESH_ABSOLUTE_DAYS)
    expires_at = min(now + timedelta(days=config.REFRESH_TOKEN_DAYS), family_expires_at)
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user.id, family_id=family_id, token_hash=hash_token(raw),
                        created_at=now, expires_at=expires_at,
                        family_expires_at=family_expires_at))
    return raw, int((expires_at - now).total_seconds())


def revoke_family(db: Session, family_id: str) -> None:
    db.execute(update(RefreshToken)
               .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()).execution_options(synchronize_session=False))


def revoke_all_for_user(db: Session, user_id: int) -> None:
    db.execute(update(RefreshToken)
               .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
               .values(revoked_at=utcnow()).execution_options(synchronize_session=False))


def revoke_by_raw(db: Session, raw: str) -> None:
    """Logout de UM dispositivo: revoga a família do token apresentado (idempotente)."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if row is not None:
        revoke_family(db, row.family_id)
        db.commit()


def _reuse_error() -> AppError:
    return AppError(401, "refresh_reutilizado", _MSG, {"WWW-Authenticate": "Bearer"})


def rotate(db: Session, raw: str) -> dict:
    """Valida o refresh, consome-o e devolve o novo par de tokens."""
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if row is None:
        raise unauthorized(_MSG)
    row_id, family_id, user_id = row.id, row.family_id, row.user_id
    family_expires_at = row.family_expires_at
    now = utcnow()

    if row.revoked_at is not None or row.expires_at <= now:
        raise unauthorized(_MSG)

    if row.used_at is not None:
        # Token já trocado sendo reapresentado: ou o cliente legítimo ou o ladrão está com
        # uma cópia velha. Não dá para saber quem -> derruba a família e força novo login.
        revoke_family(db, family_id)
        db.commit()
        raise _reuse_error()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        revoke_family(db, family_id)
        db.commit()
        raise unauthorized(_MSG)

    # "Consome" o token de forma atômica: se duas requisições tentarem usar o mesmo refresh
    # ao mesmo tempo, só uma vence o UPDATE; a outra cai no ramo de reuso.
    res = db.execute(update(RefreshToken)
                     .where(RefreshToken.id == row_id, RefreshToken.used_at.is_(None),
                            RefreshToken.revoked_at.is_(None))
                     .values(used_at=now).execution_options(synchronize_session=False))
    if res.rowcount != 1:
        db.rollback()
        revoke_family(db, family_id)
        db.commit()
        raise _reuse_error()

    new_raw, refresh_ttl = issue(db, user, family_id, family_expires_at)
    db.commit()
    access, access_ttl = create_access_token(user.id, user.token_version)
    return {"access_token": access, "expires_in": access_ttl,
            "refresh_token": new_raw, "refresh_expires_in": refresh_ttl}


def purge_expired(db: Session) -> int:
    """Rode periodicamente (cron). Só apaga famílias vencidas: antes disso as linhas
    'usadas' ainda são necessárias para detectar reuso."""
    res = db.execute(delete(RefreshToken).where(RefreshToken.family_expires_at < utcnow()))
    db.commit()
    return res.rowcount
