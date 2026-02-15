from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_app_password(x_app_password: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.app_password:
        return
    if x_app_password != settings.app_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid app password")
