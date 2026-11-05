from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import require_admin
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tables")
def get_tables(_user: tuple = Depends(require_admin)) -> list[dict]:
    return admin_service.list_tables()


@router.get("/tables/{table_name}/rows")
def get_table_rows(table_name: str, _user: tuple = Depends(require_admin)) -> list[dict]:
    try:
        return admin_service.get_table_rows(table_name)
    except admin_service.AdminTableAccessError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
