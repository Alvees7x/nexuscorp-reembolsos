from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Department
from ..schemas import DepartmentOut

router = APIRouter(prefix="/departments", tags=["Departamentos"])


@router.get("", response_model=list[DepartmentOut],
            summary="Lista departamentos (público: necessário ao cadastro; só id e nome)")
def list_departments(db: Session = Depends(get_db)):
    return db.scalars(select(Department).order_by(Department.name)).all()
