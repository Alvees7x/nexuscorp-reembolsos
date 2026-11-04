"""Executa os cenários 01–08 contra a API (banco em memória) e grava docs/EVIDENCIAS.md.
Uso (na raiz do projeto):  python -m scripts.gerar_evidencias"""
import json
import os
from datetime import date

os.environ.setdefault("SECRET_KEY", "evidencias-evidencias-evidencias-0123456789")

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, make_engine
from app.main import app
from app.seed import DEMO_PASSWORD, seed

engine = make_engine("sqlite://", poolclass=StaticPool)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
with Session() as s:
    seed(s)


def _db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _db
client = TestClient(app)
out: list[str] = ["# Evidências de execução\n",
                  "Gerado automaticamente por `python -m scripts.gerar_evidencias` "
                  "(tokens abreviados).\n"]
tokens: dict[str, str] = {}


def section(title: str, note: str = ""):
    out.append(f"\n## {title}\n")
    if note:
        out.append(note + "\n")


def call(who, method, path, body=None):
    headers = {"Authorization": f"Bearer {tokens[who]}"} if who else {}
    r = client.request(method, path, json=body, headers=headers)
    try:
        resp = json.dumps(r.json(), ensure_ascii=False, indent=2)
    except ValueError:
        resp = "(sem corpo)"
    req = f"{method} {path}" + (f"   [{who}]" if who else "")
    if body is not None:
        shown = {k: ("***" if k == "password" else v) for k, v in body.items()}
        req += "\n" + json.dumps(shown, ensure_ascii=False, indent=2)
    if "access_token" in resp:
        resp = resp.replace(r.json()["access_token"], r.json()["access_token"][:16] + "…")
    out.append(f"```http\n{req}\n```\n**→ HTTP {r.status_code}**\n```json\n{resp}\n```\n")
    return r


def new(who, **over):
    body = {"category": "transporte", "amount": "180.00", "expense_date": date.today().isoformat(),
            "justification": "Deslocamento para cliente", "receipt_ref": f"NF-{len(out):05d}"}
    body.update(over)
    return call(who, "POST", "/expenses", body).json()["id"]


for u in ["ana", "bruno", "patricia", "carlos", "marina", "fernando"]:
    r = client.post("/auth/login", json={"email": f"{u}@nexuscorp.com", "password": DEMO_PASSWORD})
    tokens[u] = r.json()["access_token"]

section("Cenário 01 — Acesso indevido")
b = new("bruno", amount="999.99", receipt_ref="NF-BRUNO-1")
call("ana", "GET", f"/expenses/{b}")

section("Cenário 02 — Gestor de outro departamento")
e = new("bruno", receipt_ref="NF-BRUNO-2")
call("bruno", "POST", f"/expenses/{e}/submit")
call("patricia", "POST", f"/manager/expenses/{e}/approve")
call("bruno", "GET", f"/expenses/{e}")

section("Cenário 03 — Credenciais incorretas")
call(None, "POST", "/auth/login", {"email": "ana@nexuscorp.com", "password": "senha-errada"})
call(None, "POST", "/auth/login", {"email": "inexistente@nexuscorp.com", "password": "senha-errada"})

section("Cenário 04 — Tentativa de alteração de permissões")
call(None, "POST", "/auth/register", {"name": "Mallory", "email": "m@x.com", "password": "Senha@1234",
                                      "department_id": 3, "role": "financeiro"})
call("ana", "PATCH", "/users/me", {"role": "financeiro"})
call("ana", "PATCH", "/users/me", {"department_id": 3})
call("ana", "GET", "/finance/expenses")

section("Cenário 05 — Aprovação fora da sequência")
e = new("ana", receipt_ref="NF-ANA-5")
call("ana", "POST", f"/expenses/{e}/submit")
call("marina", "POST", f"/finance/expenses/{e}/approve")

section("Cenário 06 — Manipulação após o envio (R$ 180,00 → R$ 1.800,00)")
call("ana", "PATCH", f"/expenses/{e}", {"amount": "1800.00"})
call("ana", "GET", f"/expenses/{e}")

section("Cenário 07 — Consulta com filtros")
t = new("bruno", receipt_ref="NF-BRUNO-7")
call("bruno", "POST", f"/expenses/{t}/submit")
call("patricia", "GET", "/manager/expenses?status=aguardando_gestor")
call("patricia", "GET", "/manager/expenses?department_id=2")

section("Cenário 08 — Fluxo completo e histórico")
f = new("ana", receipt_ref="NF-ANA-8", amount="320.50", category="hospedagem")
call("ana", "POST", f"/expenses/{f}/submit")
call("patricia", "POST", f"/manager/expenses/{f}/approve", {"comment": "Despesa de cliente confirmada"})
call("marina", "POST", f"/finance/expenses/{f}/approve", {"comment": "Conferido"})
call("marina", "POST", f"/finance/expenses/{f}/pay")
call("ana", "GET", f"/expenses/{f}/history")
call("ana", "PATCH", f"/expenses/{f}", {"amount": "1.00"})

section("Extra — Recusa sem justificativa (RN11) e autoaprovação (RN09)")
g = new("ana", receipt_ref="NF-ANA-9")
call("ana", "POST", f"/expenses/{g}/submit")
call("patricia", "POST", f"/manager/expenses/{g}/reject", {})
call("patricia", "POST", f"/manager/expenses/{g}/reject", {"comment": "Comprovante ilegível"})
h = new("patricia", receipt_ref="NF-PAT-1")
call("patricia", "POST", f"/expenses/{h}/submit")
call("patricia", "POST", f"/manager/expenses/{h}/approve")

os.makedirs("docs", exist_ok=True)
with open("docs/EVIDENCIAS.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("docs/EVIDENCIAS.md gerado")
