"""Rate limit aplicado à API: políticas + dependências do FastAPI.

Camadas (todas devolvem 429 + Retry-After no formato de erro padrão da API):
  1. global por IP   -> todas as rotas (barra scanners/flood antes de tocar no banco)
  2. por usuário     -> rotas autenticadas (um usuário não monopoliza a API)
  3. login           -> por IP  e  por IP+e-mail (força bruta / credential stuffing)
  4. register / refresh -> por IP

Os limites vêm de `config` e são lidos A CADA chamada (facilita testes com monkeypatch).
"""
from typing import Callable

from fastapi import Depends, Request

from . import config
from .deps import get_current_user
from .errors import AppError
from .models import User
from .ratelimit import SlidingWindowLimiter

limiter = SlidingWindowLimiter()   # troque por uma versão Redis ao ter mais de 1 processo


def client_ip(request: Request) -> str:
    # Atrás de proxy, use `uvicorn --proxy-headers --forwarded-allow-ips=...`: o uvicorn já
    # corrige request.client. NÃO leia X-Forwarded-For aqui: o cliente consegue forjá-lo.
    return request.client.host if request.client else "desconhecido"


def _enforce(scope: str, ident: str, rule: tuple[int, int]) -> None:
    if not config.RATE_LIMIT_ENABLED:
        return
    limit, window = rule
    d = limiter.hit(f"{scope}:{ident}", limit, window)
    if not d.allowed:
        raise AppError(
            429, "limite_excedido", "Muitas requisições. Tente novamente em instantes.",
            {"Retry-After": str(d.retry_after), "X-RateLimit-Limit": str(d.limit),
             "X-RateLimit-Remaining": "0"})


def _ip_rule(scope: str, rule: Callable[[], tuple[int, int]]):
    def dependency(request: Request) -> None:
        _enforce(scope, client_ip(request), rule())
    return dependency


# ---- dependências de roteador (aplicadas em main.py) ----
ip_limit = _ip_rule("global-ip", lambda: config.RATE_LIMIT_GLOBAL_IP)


def user_limit(user: User = Depends(get_current_user)) -> None:
    # get_current_user é cacheado pelo FastAPI na mesma requisição: não duplica a consulta.
    _enforce("user", str(user.id), config.RATE_LIMIT_USER)


# ---- dependências por endpoint ----
login_ip_limit = _ip_rule("login-ip", lambda: config.RATE_LIMIT_LOGIN_IP)
register_ip_limit = _ip_rule("register-ip", lambda: config.RATE_LIMIT_REGISTER_IP)
refresh_ip_limit = _ip_rule("refresh-ip", lambda: config.RATE_LIMIT_REFRESH_IP)


def check_login_email(request: Request, email: str) -> None:
    """Chamado DENTRO do endpoint de login (o e-mail só existe depois de ler o corpo).
    A chave é IP+e-mail: quem erra a senha de ana@ não consegue bloquear a ana de outro IP."""
    _enforce("login-email", f"{client_ip(request)}|{email.strip().lower()}",
             config.RATE_LIMIT_LOGIN_EMAIL)
