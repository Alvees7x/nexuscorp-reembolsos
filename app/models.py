from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (CheckConstraint, Date, DateTime, Enum as SAEnum, ForeignKey,
                        Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import Category, Decision, Role, Stage, Status


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # UTC


def _enum(cls, length=30):
    return SAEnum(cls, native_enum=False, length=length, create_constraint=False,
                  values_callable=lambda e: [m.value for m in e])


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    users: Mapped[list["User"]] = relationship(back_populates="department")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # nunca a senha em texto (RN13)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    role: Mapped[Role] = mapped_column(_enum(Role))
    is_active: Mapped[bool] = mapped_column(default=True)
    token_version: Mapped[int] = mapped_column(default=0)  # incrementar invalida os tokens (RN14)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    department: Mapped[Department] = relationship(back_populates="users")
    expenses: Mapped[list["ExpenseRequest"]] = relationship(back_populates="requester")


class ExpenseRequest(Base):
    __tablename__ = "expense_requests"
    __table_args__ = (
        UniqueConstraint("requester_id", "receipt_ref", name="uq_requester_receipt"),  # RN05
        CheckConstraint("amount > 0", name="ck_amount_positive"),                       # RN04
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[Category] = mapped_column(_enum(Category))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    expense_date: Mapped[date] = mapped_column(Date)
    justification: Mapped[str] = mapped_column(Text)
    receipt_ref: Mapped[str] = mapped_column(String(100))
    status: Mapped[Status] = mapped_column(_enum(Status), default=Status.DRAFT, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    requester: Mapped[User] = relationship(back_populates="expenses")
    history: Mapped[list["ReviewHistory"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan", order_by="ReviewHistory.id")


class ReviewHistory(Base):
    __tablename__ = "review_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    expense_id: Mapped[int] = mapped_column(ForeignKey("expense_requests.id"), index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stage: Mapped[Stage] = mapped_column(_enum(Stage))
    decision: Mapped[Decision] = mapped_column(_enum(Decision))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    expense: Mapped[ExpenseRequest] = relationship(back_populates="history")
    reviewer: Mapped[User] = relationship()
