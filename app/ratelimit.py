"""Núcleo do rate limit — sem dependência de FastAPI (fácil de testar e de trocar por Redis).

Algoritmo: janela deslizante com log de timestamps ("sliding window log").
 - Guarda, por chave, os instantes das últimas requisições PERMITIDAS.
 - Uma nova requisição é aceita se houver menos de `limit` instantes dentro dos últimos
   `window` segundos. Não existe o "efeito borda" da janela fixa (2x o limite na virada).
 - Requisições BLOQUEADAS não são registradas: martelar o endpoint não prolonga o bloqueio.
 - Custo de memória: O(limit) por chave ativa. Chaves ociosas são varridas periodicamente.

Limites desta implementação (de propósito, para a v1):
 - Estado em memória do PROCESSO. Com N workers/instâncias, o limite efetivo vira N x limit.
   Para produção com mais de um processo, implemente a mesma interface `hit/reset` sobre
   Redis (ex.: script Lua com INCR+EXPIRE ou ZSET) e troque a instância em `limits.py`.
"""
import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int  # segundos até liberar (0 quando permitido)


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic, sweep_every: int = 1000):
        self._clock = clock                      # injetável: testes usam um relógio falso
        self._hits: dict[str, deque[float]] = {}
        self._expires: dict[str, float] = {}     # quando a chave pode ser descartada
        self._lock = threading.Lock()            # endpoints `def` rodam em threads
        self._sweep_every = sweep_every
        self._ops = 0

    def hit(self, key: str, limit: int, window: int) -> Decision:
        now = self._clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            cutoff = now - window
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                retry = max(1, math.ceil(q[0] + window - now))
                return Decision(False, limit, 0, retry)
            q.append(now)
            self._expires[key] = now + window
            self._ops += 1
            if self._ops % self._sweep_every == 0:
                self._sweep(now)
            return Decision(True, limit, limit - len(q), 0)

    def _sweep(self, now: float) -> None:
        for k in [k for k, exp in self._expires.items() if exp <= now]:
            self._hits.pop(k, None)
            self._expires.pop(k, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
            self._expires.clear()
            self._ops = 0
