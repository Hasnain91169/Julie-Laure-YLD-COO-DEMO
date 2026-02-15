from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AutomationTypeEnum


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pain_point_id: Mapped[int] = mapped_column(ForeignKey("pain_points.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    impact_hours_per_week: Mapped[float] = mapped_column(Float, nullable=False)
    effort_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    automation_type: Mapped[AutomationTypeEnum] = mapped_column(Enum(AutomationTypeEnum), nullable=False)
    suggested_solution: Mapped[str] = mapped_column(Text, nullable=False)
    dependencies: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    quick_win: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    pain_point = relationship("PainPoint", back_populates="score")
