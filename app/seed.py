"""Dados de demonstração (idempotente). Uso: python -m app.seed
Senha de TODOS os usuários de demonstração: Senha@123 (apenas para ambiente de teste)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .enums import Role
from .models import Department, User
from .security import hash_password

DEMO_PASSWORD = "Senha@123"
DEPARTMENTS = ["Comercial", "Tecnologia", "Financeiro"]
USERS = [  # nome, e-mail, departamento, perfil
    ("Ana", "ana@nexuscorp.com", "Comercial", Role.EMPLOYEE),
    ("Bruno", "bruno@nexuscorp.com", "Tecnologia", Role.EMPLOYEE),
    ("Patrícia", "patricia@nexuscorp.com", "Comercial", Role.MANAGER),
    ("Carlos", "carlos@nexuscorp.com", "Tecnologia", Role.MANAGER),
    ("Fernando", "fernando@nexuscorp.com", "Financeiro", Role.MANAGER),  # aprova despesas de quem é do Financeiro
    ("Marina", "marina@nexuscorp.com", "Financeiro", Role.FINANCE),
]


def seed(db: Session) -> None:
    for name in DEPARTMENTS:
        if db.scalar(select(Department).where(Department.name == name)) is None:
            db.add(Department(name=name))
    db.commit()
    depts = {d.name: d.id for d in db.scalars(select(Department))}
    for name, email, dept, role in USERS:
        if db.scalar(select(User).where(User.email == email)) is None:
            db.add(User(name=name, email=email, password_hash=hash_password(DEMO_PASSWORD),
                        department_id=depts[dept], role=role))
    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed(session)
    print("Seed concluído. Usuários:", ", ".join(u[1] for u in USERS), "| senha:", DEMO_PASSWORD)
