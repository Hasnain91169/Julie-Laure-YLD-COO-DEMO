from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_app_password(x_app_password: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.app_password:
        return
    if x_app_password != settings.app_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid app password")


def require_webhook_secret(expected_secret: str | None, x_webhook_secret: str | None = Header(default=None)) -> None:
    """Validate webhook secret header against expected secret.

    Args:
        expected_secret: The secret to validate against (from settings)
        x_webhook_secret: The secret from request header

    Raises:
        HTTPException: 401 if secret doesn't match
    """
    if not expected_secret:
        return  # No secret configured, allow request
    if x_webhook_secret != expected_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")
