from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

NameStr = Annotated[str, Field(min_length=1, max_length=200)]


class DepartmentCreate(BaseModel):
    name: NameStr
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class DepartmentUpdate(BaseModel):
    name: NameStr | None = None
    parent_id: int | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class DepartmentOut(BaseModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DepartmentTree(BaseModel):
    department: DepartmentOut
    employees: list["EmployeeOut"] = []
    children: list["DepartmentTree"] = []


from app.schemas.employee import EmployeeOut  # noqa: E402
