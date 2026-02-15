from abc import ABC, abstractmethod
from typing import Any

from app.schemas.intake import CanonicalIntake


class IntakeAdapter(ABC):
    @abstractmethod
    def to_canonical(self, payload: dict[str, Any]) -> CanonicalIntake:
        raise NotImplementedError
