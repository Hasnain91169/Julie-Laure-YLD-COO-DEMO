from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import PainCategoryEnum


class PainPoint(Base):
    __tablename__ = "pain_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[PainCategoryEnum] = mapped_column(Enum(PainCategoryEnum), default=PainCategoryEnum.other, nullable=False, index=True)
    frequency_per_week: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    minutes_per_occurrence: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    people_affected: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    systems_involved: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_workaround: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_modes: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitive_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    redaction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    interview = relationship("Interview", back_populates="pain_points")
    score = relationship("Score", back_populates="pain_point", uselist=False, cascade="all, delete-orphan")
