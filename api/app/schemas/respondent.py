from datetime import datetime

from pydantic import BaseModel, EmailStr


class RespondentCreate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    team: str
    role: str
    location: str | None = None
    consent: bool = False


class RespondentUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    team: str | None = None
    role: str | None = None
    location: str | None = None
    consent: bool | None = None


class RespondentRead(BaseModel):
    id: int
    name: str | None
    email: str | None
    team: str
    role: str
    location: str | None
    consent: bool
    created_at: datetime

    model_config = {"from_attributes": True}
