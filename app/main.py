from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .database import Base, engine
from .errors import AppError
from .routers import auth, departments, expenses, finance, manager


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title="NexusCorp — API de Gestão de Reembolsos",
    version="1.0.0",
    description=("Autenticação via JWT (Bearer). Fluxo: rascunho → aguardando_gestor → "
                 "aguardando_financeiro → aprovada → paga (ou recusada)."),
    lifespan=lifespan,
)


@app.exception_handler(AppError)
async def app_error_handler(_req: Request, exc: AppError):
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}},
                        status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(_req: Request, exc: RequestValidationError):
    # Não devolve o valor enviado ("input"): evita eco de senhas e outros dados sensíveis (RN13).
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
               for e in exc.errors()]
    return JSONResponse({"error": {"code": "dados_invalidos",
                                   "message": "Os dados enviados são inválidos",
                                   "details": details}}, status_code=422)


for r in (auth.router, departments.router, expenses.router, manager.router, finance.router):
    app.include_router(r)


@app.get("/health", tags=["Infra"])
def health():
    return {"status": "ok"}
