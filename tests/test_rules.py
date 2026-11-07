"""Regras de negócio RN01–RN15 não cobertas diretamente pelos cenários."""
from datetime import date, timedelta

from sqlalchemy import select

from app.models import User

from .helpers import create, create_and_submit, payload


def test_rn01_sem_token(client):
    assert client.get("/expenses").status_code == 401
    assert client.get("/expenses", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_rn04_valor_invalido(client, auth):
    for bad in ("0", "-5", "0.00"):
        assert client.post("/expenses", json=payload(amount=bad), headers=auth("ana")).status_code == 422
    assert client.post("/expenses", json=payload(amount="10.123"), headers=auth("ana")).status_code == 422


def test_rn05_comprovante_duplicado(client, auth):
    create(client, auth("ana"), receipt_ref="NF-DUP")
    r = client.post("/expenses", json=payload(receipt_ref="nf-dup"), headers=auth("ana"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "comprovante_duplicado"
    # outro colaborador pode usar a mesma referência (a regra é por colaborador)
    assert client.post("/expenses", json=payload(receipt_ref="NF-DUP"), headers=auth("bruno")).status_code == 201


def test_rn06_data_futura(client, auth):
    future = (date.today() + timedelta(days=1)).isoformat()
    assert client.post("/expenses", json=payload(expense_date=future), headers=auth("ana")).status_code == 422


def test_rn07_edicao_em_rascunho(client, auth):
    ana = auth("ana")
    e = create(client, ana)
    r = client.patch(f"/expenses/{e['id']}", json={"amount": "50.00"}, headers=ana)
    assert r.status_code == 200 and r.json()["amount"] == "50.00"
    assert client.delete(f"/expenses/{e['id']}", headers=ana).status_code == 204
    assert client.get(f"/expenses/{e['id']}", headers=ana).status_code == 404


def test_rn09_autoaprovacao(client, auth):
    e = create_and_submit(client, auth("patricia"))
    r = client.post(f"/manager/expenses/{e['id']}/approve", headers=auth("patricia"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "segregacao_de_funcoes"
    # despesa do financeiro: passa pelo gestor do Financeiro e não pode ser aprovada por ela mesma
    f = create_and_submit(client, auth("marina"))
    assert client.post(f"/manager/expenses/{f['id']}/approve", headers=auth("fernando")).status_code == 200
    assert client.post(f"/finance/expenses/{f['id']}/approve", headers=auth("marina")).status_code == 403


def test_rn11_recusa_exige_justificativa(client, auth):
    e = create_and_submit(client, auth("ana"))
    url = f"/manager/expenses/{e['id']}/reject"
    assert client.post(url, json={}, headers=auth("patricia")).status_code == 422
    assert client.post(url, json={"comment": "  "}, headers=auth("patricia")).status_code == 422
    r = client.post(url, json={"comment": "Sem comprovante legível"}, headers=auth("patricia"))
    assert r.status_code == 200 and r.json()["status"] == "recusada"
    hist = client.get(f"/expenses/{e['id']}/history", headers=auth("ana")).json()
    assert hist[-1]["decision"] == "recusada" and hist[-1]["comment"] == "Sem comprovante legível"
    assert client.post(f"/manager/expenses/{e['id']}/approve", headers=auth("patricia")).status_code == 409


def test_financeiro_so_ve_o_que_foi_encaminhado(client, auth):
    e = create_and_submit(client, auth("ana"))
    assert client.get("/finance/expenses", headers=auth("marina")).json() == []
    assert client.get(f"/expenses/{e['id']}", headers=auth("marina")).status_code == 404
    client.post(f"/manager/expenses/{e['id']}/approve", headers=auth("patricia"))
    r = client.get("/finance/expenses?department_id=1&status=aguardando_financeiro", headers=auth("marina"))
    assert [x["id"] for x in r.json()] == [e["id"]]


def test_rascunho_e_privado(client, auth):
    e = create(client, auth("ana"))
    assert client.get(f"/expenses/{e['id']}", headers=auth("patricia")).status_code == 404
    assert client.post(f"/finance/expenses/{e['id']}/approve", headers=auth("marina")).status_code == 404


def test_rn13_credenciais_nao_vazam(client, auth, Session):
    ana = auth("ana")
    assert "password" not in client.get("/users/me", headers=ana).text
    r = client.post("/auth/register", json={"name": "Xx", "email": "x@x.com", "password": "Senha@1234",
                                            "department_id": 1})
    assert "password" not in r.text and "hash" not in r.text
    bad = client.post("/auth/register", json={"name": "Yy", "email": "y@y.com", "password": "curta",
                                              "department_id": 1})
    assert bad.status_code == 422 and "curta" not in bad.text  # a validação não ecoa a senha
    with Session() as s:
        stored = s.scalar(select(User.password_hash).where(User.email == "x@x.com"))
    assert stored is not None and stored.startswith("scrypt$") and "Senha@1234" not in stored


def test_rn14_logout_invalida_token(client, auth):
    ana = auth("ana")
    assert client.get("/expenses", headers=ana).status_code == 200
    assert client.post("/auth/logout", headers=ana).status_code == 204
    assert client.get("/expenses", headers=ana).status_code == 401


def test_rn14_usuario_desativado(client, auth, Session):
    ana = auth("ana")
    with Session() as s:
        u = s.scalar(select(User).where(User.email == "ana@nexuscorp.com"))
        u.is_active = False
        s.commit()
    assert client.get("/expenses", headers=ana).status_code == 401
