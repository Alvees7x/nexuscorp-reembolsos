"""Cenários 01–08 da homologação (seção 7 do enunciado)."""
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt

from .helpers import create, create_and_submit, payload


def test_c01_acesso_indevido(client, auth):
    bruno = create(client, auth("bruno"), amount="999.99")
    r = client.get(f"/expenses/{bruno['id']}", headers=auth("ana"))
    assert r.status_code == 404
    assert "999" not in r.text and "amount" not in r.text
    assert client.get(f"/expenses/{bruno['id']}/history", headers=auth("ana")).status_code == 404


def test_c02_gestor_de_outro_departamento(client, auth):
    e = create_and_submit(client, auth("bruno"))
    r = client.post(f"/manager/expenses/{e['id']}/approve", headers=auth("patricia"))
    assert r.status_code == 404
    assert client.get(f"/expenses/{e['id']}", headers=auth("bruno")).json()["status"] == "aguardando_gestor"
    assert len(client.get(f"/expenses/{e['id']}/history", headers=auth("bruno")).json()) == 1  # só o envio


def test_c03_credenciais_incorretas(client):
    wrong = client.post("/auth/login", json={"email": "ana@nexuscorp.com", "password": "errada"})
    unknown = client.post("/auth/login", json={"email": "ninguem@nexuscorp.com", "password": "errada"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # não revela se o e-mail existe
    assert "hash" not in wrong.text.lower() and "scrypt" not in wrong.text


def test_c04_tentativa_de_elevar_permissoes(client, auth, Session):
    # cadastro com perfil/departamento forjado
    r = client.post("/auth/register", json={"name": "Mallory", "email": "m@x.com", "password": "Senha@1234",
                                            "department_id": 1, "role": "financeiro"})
    assert r.status_code == 422
    # cadastro legítimo sempre vira colaborador
    r = client.post("/auth/register", json={"name": "Mallory", "email": "m@x.com",
                                            "password": "Senha@1234", "department_id": 1})
    assert r.status_code == 201 and r.json()["role"] == "colaborador"
    # atualização comum não aceita role nem department
    ana = auth("ana")
    assert client.patch("/users/me", json={"role": "financeiro"}, headers=ana).status_code == 422
    assert client.patch("/users/me", json={"department_id": 3}, headers=ana).status_code == 422
    assert client.get("/users/me", headers=ana).json()["role"] == "colaborador"
    # rotas do financeiro/gestor continuam fechadas
    assert client.get("/finance/expenses", headers=ana).status_code == 403
    assert client.get("/manager/expenses", headers=ana).status_code == 403
    # token forjado com role=financeiro, assinado com outra chave
    forged = jwt.encode({"sub": "1", "ver": 0, "role": "financeiro",
                         "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "outra-chave", "HS256")
    assert client.get("/finance/expenses", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_c05_aprovacao_fora_da_sequencia(client, auth):
    e = create_and_submit(client, auth("ana"))
    r = client.post(f"/finance/expenses/{e['id']}/approve", headers=auth("marina"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "transicao_invalida"
    assert client.post(f"/finance/expenses/{e['id']}/pay", headers=auth("marina")).status_code == 409
    assert client.get(f"/expenses/{e['id']}", headers=auth("ana")).json()["status"] == "aguardando_gestor"


def test_c06_manipulacao_apos_envio(client, auth):
    ana = auth("ana")
    e = create_and_submit(client, ana, amount="180.00")
    r = client.patch(f"/expenses/{e['id']}", json={"amount": "1800.00"}, headers=ana)
    assert r.status_code == 409
    assert client.delete(f"/expenses/{e['id']}", headers=ana).status_code == 409
    assert Decimal(client.get(f"/expenses/{e['id']}", headers=ana).json()["amount"]) == Decimal("180.00")
    # tentativa de forçar o status pelo payload
    assert client.patch(f"/expenses/{e['id']}", json={"status": "aprovada"}, headers=ana).status_code == 422


def test_c07_consulta_com_filtros(client, auth):
    a = create_and_submit(client, auth("ana"), category="alimentacao")
    b = create_and_submit(client, auth("bruno"), category="alimentacao")
    create(client, auth("ana"))  # rascunho: gestor não vê
    r = client.get("/manager/expenses?status=aguardando_gestor", headers=auth("patricia"))
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert ids == {a["id"]}
    assert {x["requester"]["department"]["name"] for x in r.json()} == {"Comercial"}
    assert b["id"] not in ids
    assert client.get("/manager/expenses?department_id=2", headers=auth("patricia")).status_code == 403
    assert client.get("/manager/expenses?category=transporte", headers=auth("patricia")).json() == []


def test_c08_historico_financeiro(client, auth):
    ana = auth("ana")
    e = create_and_submit(client, ana)
    i = e["id"]
    assert client.post(f"/manager/expenses/{i}/approve", json={"comment": "ok"}, headers=auth("patricia")).status_code == 200
    assert client.post(f"/finance/expenses/{i}/approve", headers=auth("marina")).json()["status"] == "aprovada"
    assert client.post(f"/finance/expenses/{i}/pay", headers=auth("marina")).json()["status"] == "paga"
    hist = client.get(f"/expenses/{i}/history", headers=ana).json()
    assert [(h["stage"], h["decision"], h["reviewer"]["name"]) for h in hist] == [
        ("colaborador", "enviada", "Ana"), ("gestor", "aprovada", "Patrícia"),
        ("financeiro", "aprovada", "Marina"), ("financeiro", "paga", "Marina")]
    assert all(h["created_at"] for h in hist)
    # encerrada: não muda mais
    assert client.patch(f"/expenses/{i}", json={"justification": "outra coisa"}, headers=ana).status_code == 409
    assert client.post(f"/manager/expenses/{i}/approve", headers=auth("patricia")).status_code == 409
