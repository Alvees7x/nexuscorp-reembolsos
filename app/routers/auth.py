from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..enums import Role
from ..errors import AppError, conflict, invalid
from ..models import Department, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut, UserUpdateIn
from ..security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(tags=["Autenticação e usuários"])


@router.post("/auth/register", response_model=UserOut, status_code=201,
             summary="Cadastro (sempre com perfil colaborador)")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.get(Department, data.department_id) is None:
        raise invalid("Departamento inexistente")
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise conflict("E-mail já cadastrado", "email_duplicado")
    # RN15: o perfil NUNCA vem do cliente; o schema nem aceita o campo `role`.
    user = User(name=data.name, email=email, password_hash=hash_password(data.password),
                department_id=data.department_id, role=Role.EMPLOYEE)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise conflict("E-mail já cadastrado", "email_duplicado")
    return user


@router.post("/auth/login", response_model=TokenOut, summary="Autenticação")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    # Sempre calcula um hash, exista o usuário ou não (resposta e tempo uniformes).
    ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not ok or not user.is_active:
        raise AppError(401, "credenciais_invalidas", "E-mail ou senha inválidos",
                       {"WWW-Authenticate": "Bearer"})
    token, expires_in = create_access_token(user.id, user.token_version)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.post("/auth/logout", status_code=204, summary="Encerra todas as sessões do usuário")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.token_version += 1  # invalida todos os tokens já emitidos (RN14)
    db.commit()
    return Response(status_code=204)


@router.get("/users/me", response_model=UserOut, summary="Dados do usuário autenticado")
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/users/me", response_model=UserOut, summary="Atualiza o próprio nome")
def update_me(data: UserUpdateIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    user.name = data.name
    db.commit()
    return user
