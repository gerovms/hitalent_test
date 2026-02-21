from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

Text200 = Annotated[str, Field(min_length=1, max_length=200)]


class EmployeeCreate(BaseModel):
    full_name: Text200
    position: Text200
    hired_at: date | None = None

    @field_validator("full_name", "position")
    @classmethod
    def trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class EmployeeOut(BaseModel):
    id: int
    department_id: int
    full_name: str
    position: str
    hired_at: date | None
    created_at: datetime

    model_config = {"from_attributes": True}
