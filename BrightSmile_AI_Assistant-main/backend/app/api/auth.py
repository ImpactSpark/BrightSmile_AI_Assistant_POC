from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.security import verify_password
from app.dependencies import SESSION_COOKIE_NAME, get_auth_storage, get_current_user, get_storage
from app.services.gallery_service import GalleryService
from app.storage.auth_interface import AuthStorage
from app.storage.interface import CaseStorage

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_MAX_AGE = 7 * 24 * 60 * 60


class LoginRequest(BaseModel):
    id: str
    password: str


class MeResponse(BaseModel):
    role: str
    id: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


@router.get("/doctors")
def list_known_doctors(storage: CaseStorage = Depends(get_storage)) -> list[str]:
    """Public list of doctor names, for the login screen's 'unknown user' hint."""
    return [d.name for d in GalleryService(storage).list_doctors()]


@router.post("/doctor/login", response_model=MeResponse)
def doctor_login(
    body: LoginRequest,
    response: Response,
    auth: AuthStorage = Depends(get_auth_storage),
) -> MeResponse:
    stored_hash = auth.get_doctor_password_hash(body.id)
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="unknown dentist name")
    if not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = auth.create_session("doctor", body.id)
    _set_session_cookie(response, token)
    return MeResponse(role="doctor", id=body.id)


@router.post("/patient/login", response_model=MeResponse)
def patient_login(
    body: LoginRequest, response: Response, auth: AuthStorage = Depends(get_auth_storage)
) -> MeResponse:
    stored_hash = auth.get_patient_password_hash(body.id)
    if not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = auth.create_session("patient", body.id)
    _set_session_cookie(response, token)
    return MeResponse(role="patient", id=body.id)


class AdminLoginRequest(BaseModel):
    password: str


@router.post("/admin/login", response_model=MeResponse)
def admin_login(
    body: AdminLoginRequest, response: Response, auth: AuthStorage = Depends(get_auth_storage)
) -> MeResponse:
    stored_hash = auth.get_admin_password_hash()
    if not verify_password(body.password, stored_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = auth.create_session("admin", "admin")
    _set_session_cookie(response, token)
    return MeResponse(role="admin", id="admin")


@router.post("/admin/reset-password")
def reset_admin_password(auth: AuthStorage = Depends(get_auth_storage)) -> dict:
    auth.reset_admin_password()
    return {"status": "ok"}


@router.post("/logout")
def logout(
    response: Response,
    bsai_session: str | None = Cookie(default=None),
    auth: AuthStorage = Depends(get_auth_storage),
) -> dict:
    if bsai_session:
        auth.delete_session(bsai_session)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "ok"}


class ResetPasswordRequest(BaseModel):
    id: str


@router.post("/doctor/reset-password")
def reset_doctor_password(
    body: ResetPasswordRequest, auth: AuthStorage = Depends(get_auth_storage)
) -> dict:
    auth.reset_doctor_password(body.id)
    return {"status": "ok"}


@router.post("/patient/reset-password")
def reset_patient_password(
    body: ResetPasswordRequest, auth: AuthStorage = Depends(get_auth_storage)
) -> dict:
    auth.reset_patient_password(body.id)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(user: tuple[str, str] = Depends(get_current_user)) -> MeResponse:
    role, subject_id = user
    return MeResponse(role=role, id=subject_id)
