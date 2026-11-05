from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymysql.err import IntegrityError

from app.config import settings
from app.schemas.auth import Credentials, NewUser, PasswordReset, UserActiveUpdate
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["authentication"])


def get_optional_user(request: Request) -> dict | None:
    return auth_service.get_session_user(request.cookies.get(auth_service.SESSION_COOKIE))


def require_user(user: dict | None = Depends(get_optional_user)) -> dict:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return user


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth_service.SESSION_COOKIE,
        token,
        max_age=auth_service.SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path="/",
    )


@router.get("/status")
def auth_status(user: dict | None = Depends(get_optional_user)) -> dict:
    setup_required = auth_service.setup_required()
    return {
        "setup_required": setup_required,
        "registration_enabled": settings.allow_public_registration and not setup_required,
        "password_recovery_enabled": auth_service.password_recovery_enabled(),
        "user": user,
    }


@router.post("/password-reset")
def reset_password(credentials: PasswordReset) -> dict:
    if not auth_service.password_recovery_enabled():
        raise HTTPException(status_code=503, detail="Password recovery is not configured on this server.")
    try:
        reset = auth_service.reset_password(
            credentials.username,
            credentials.recovery_key,
            credentials.new_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not reset:
        raise HTTPException(status_code=400, detail="Unable to reset password. Check the username and recovery key.")
    return {"message": "Password reset. Sign in with the new password."}


@router.post("/setup")
def setup_admin(credentials: Credentials, response: Response) -> dict:
    if not auth_service.setup_required():
        raise HTTPException(status_code=409, detail="Initial admin account has already been created.")
    try:
        auth_service.create_initial_admin(credentials.username, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    user, token = auth_service.login(credentials.username, credentials.password)
    _set_session_cookie(response, token)
    return user


@router.post("/login")
def sign_in(credentials: Credentials, response: Response) -> dict:
    user_session = auth_service.login(credentials.username, credentials.password)
    if user_session is None:
        raise HTTPException(status_code=401, detail="Username or password is incorrect.")
    user, token = user_session
    _set_session_cookie(response, token)
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, response: Response) -> dict:
    if not settings.allow_public_registration:
        raise HTTPException(status_code=403, detail="Public registration is disabled.")
    if auth_service.setup_required():
        raise HTTPException(status_code=409, detail="Create the initial administrator account first.")
    try:
        auth_service.create_user(credentials.username, credentials.password, role="user")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IntegrityError as error:
        if error.args and error.args[0] == 1062:
            raise HTTPException(status_code=409, detail="That username is already in use.") from error
        raise

    user_session = auth_service.login(credentials.username, credentials.password)
    if user_session is None:
        raise HTTPException(status_code=500, detail="Account created, but sign-in failed.")
    user, token = user_session
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=204)
def sign_out(request: Request, response: Response) -> Response:
    auth_service.logout(request.cookies.get(auth_service.SESSION_COOKIE))
    response.delete_cookie(
        auth_service.SESSION_COOKIE,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me")
def current_user(user: dict = Depends(require_user)) -> dict:
    return user


@router.get("/users")
def users(_admin: dict = Depends(require_admin)) -> list[dict]:
    return auth_service.list_users()


@router.post("/users", status_code=201)
def create_user(user_data: NewUser, _admin: dict = Depends(require_admin)) -> dict:
    try:
        return auth_service.create_user(user_data.username, user_data.password, user_data.role)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IntegrityError as error:
        if error.args and error.args[0] == 1062:
            raise HTTPException(status_code=409, detail="That username is already in use.") from error
        raise


@router.patch("/users/{user_id}")
def update_user(user_id: str, update: UserActiveUpdate, admin: dict = Depends(require_admin)) -> dict:
    if user_id == admin["id"] and not update.is_active:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    if not auth_service.set_user_active(user_id, update.is_active):
        raise HTTPException(status_code=404, detail="User not found.")
    return {"id": user_id, "is_active": update.is_active}