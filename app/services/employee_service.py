from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Department, Employee


class EmployeeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self,
                     dep_id: int,
                     *,
                     full_name: str,
                     position: str,
                     hired_at) -> Employee:
        dep = await self.session.get(Department, dep_id)
        if dep is None:
            raise KeyError("department not found")

        emp = Employee(
            department_id=dep_id,
            full_name=full_name.strip(),
            position=position.strip(),
            hired_at=hired_at,
        )
        self.session.add(emp)
        await self.session.commit()
        await self.session.refresh(emp)
        return emp
