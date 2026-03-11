"""
Endpoints de la API para Mesas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas import TableCreate, TableUpdate, TableResponse, TableAvailability
from app.models import Table, Reservation
from app.services.auth_service import require_admin
from app.schemas.auth import UserInDB

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("/", response_model=List[TableResponse])
def list_tables(
    only_active: bool = True,
    db: Session = Depends(get_db)
):
    """
    **Lista todas las mesas** del restaurante. Endpoint público.
    """
    query = db.query(Table)
    if only_active:
        query = query.filter(Table.is_active == True)
    return query.all()


@router.post("/", response_model=TableResponse, status_code=status.HTTP_201_CREATED)
def create_table(
    table: TableCreate,
    db: Session = Depends(get_db),
    _: UserInDB = Depends(require_admin)
):
    """
    **Crea una nueva mesa**. Requiere autenticación de administrador.
    """
    existing = db.query(Table).filter(Table.name == table.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una mesa con el nombre '{table.name}'"
        )

    new_table = Table(**table.dict())
    db.add(new_table)
    db.commit()
    db.refresh(new_table)
    return new_table


@router.get("/{table_id}", response_model=TableResponse)
def get_table(
    table_id: int,
    db: Session = Depends(get_db)
):
    """
    **Obtiene una mesa específica** por ID. Endpoint público.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada"
        )
    return table


@router.put("/{table_id}", response_model=TableResponse)
def update_table(
    table_id: int,
    table_update: TableUpdate,
    db: Session = Depends(get_db),
    _: UserInDB = Depends(require_admin)
):
    """
    **Actualiza una mesa**. Requiere autenticación de administrador.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada"
        )

    update_data = table_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(table, field, value)

    db.commit()
    db.refresh(table)
    return table


@router.delete("/{table_id}")
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    _: UserInDB = Depends(require_admin)
):
    """
    **Desactiva una mesa**. Requiere autenticación de administrador.
    No la borra físicamente, solo la marca como inactiva.
    """
    table = db.query(Table).filter(Table.id == table_id).first()
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mesa no encontrada"
        )

    table.is_active = False
    db.commit()
    return {"message": "Mesa desactivada", "table_id": table_id}