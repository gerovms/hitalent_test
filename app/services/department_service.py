from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import (Integer, Select, and_, func, literal, select,
                        update)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Department, Employee
from app.exceptions import ConflictError


@dataclass(frozen=True)
class DeleteResult:
    deleted_department_id: int
    mode: str
    reassigned_to: int | None = None


class DepartmentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, name: str, parent_id: int | None) -> Department:
        name = name.strip()
        if parent_id is not None:
            parent = await self.session.get(Department, parent_id)
            if parent is None:
                raise KeyError("parent department not found")

        if await self._name_exists(name=name, parent_id=parent_id):
            raise ConflictError(
                "Department name must be unique within the same parent"
                )

        dep = Department(name=name, parent_id=parent_id)
        self.session.add(dep)
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                "Department name must be unique within the same parent"
                ) from e
        await self.session.refresh(dep)
        return dep

    async def update(self,
                     dep_id: int,
                     *,
                     name: str | None,
                     parent_id: int | None) -> Department:
        dep = await self.session.get(Department, dep_id)
        if dep is None:
            raise KeyError("department not found")

        if parent_id is not None:
            if parent_id == dep_id:
                raise ConflictError("Department cannot be parent of itself")

            new_parent = await self.session.get(Department, parent_id)
            if new_parent is None:
                raise KeyError("parent department not found")

            if await self._would_create_cycle(dep_id=dep_id,
                                              new_parent_id=parent_id):
                raise ConflictError("Cannot create a cycle in department tree")

        if name is not None:
            name = name.strip()
            target_parent = parent_id if parent_id is not None else dep.parent_id
            if await self._name_exists(name=name,
                                       parent_id=target_parent,
                                       exclude_id=dep_id):
                raise ConflictError(
                    "Department name must be unique within the same parent"
                    )
            dep.name = name

        if parent_id is not None:
            dep.parent_id = parent_id

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise ConflictError(
                "Department name must be unique within the same parent"
                ) from e

        await self.session.refresh(dep)
        return dep

    async def delete(self,
                     dep_id: int,
                     *,
                     mode: str,
                     reassign_to_department_id: int | None) -> DeleteResult:
        dep = await self.session.get(Department, dep_id)
        if dep is None:
            raise KeyError("department not found")

        if mode not in {"cascade", "reassign"}:
            raise ValueError("mode must be cascade or reassign")

        if mode == "cascade":
            await self.session.delete(dep)
            await self.session.commit()
            return DeleteResult(deleted_department_id=dep_id, mode=mode)

        if reassign_to_department_id is None:
            raise ValueError(
                "reassign_to_department_id is required when mode=reassign"
                )

        if reassign_to_department_id == dep_id:
            raise ConflictError(
                "Cannot reassign employees to the same department "
                "being deleted"
                )

        target = await self.session.get(Department, reassign_to_department_id)
        if target is None:
            raise KeyError("reassign_to_department not found")

        async with self.session.begin():
            await self.session.execute(
                update(Employee)
                .where(Employee.department_id == dep_id)
                .values(department_id=reassign_to_department_id)
            )
            await self.session.delete(dep)

        return DeleteResult(deleted_department_id=dep_id,
                            mode=mode,
                            reassigned_to=reassign_to_department_id)

    async def get_tree(self,
                       dep_id: int,
                       *,
                       depth: int,
                       include_employees: bool) -> dict[str, Any]:
        if depth < 1:
            depth = 1
        if depth > 5:
            depth = 5

        root = await self.session.get(Department, dep_id)
        if root is None:
            raise KeyError("department not found")

        lvl = literal(0, type_=Integer).label("lvl")
        cte = (
            select(Department.id, Department.parent_id, lvl)
            .where(Department.id == dep_id)
            .cte(name="dept_tree", recursive=True)
        )
        cte_alias = cte.alias()
        dep_tbl = Department.__table__

        cte = cte.union_all(
            select(dep_tbl.c.id,
                   dep_tbl.c.parent_id,
                   (cte_alias.c.lvl + 1).label("lvl"))
            .where(dep_tbl.c.parent_id == cte_alias.c.id)
            .where(cte_alias.c.lvl < depth)
        )

        rows = (await self.session.execute(select(cte.c.id,
                                                  cte.c.parent_id,
                                                  cte.c.lvl))).all()
        ids = [r.id for r in rows]

        deps = (await self.session.execute(
            select(Department).where(Department.id.in_(ids))
            )).scalars().all()
        dep_by_id = {d.id: d for d in deps}

        children_map: dict[int, list[int]] = {i: [] for i in ids}
        for r in rows:
            if r.parent_id is not None and r.parent_id in children_map:
                children_map[r.parent_id].append(r.id)

        employees_map: dict[int, list[Employee]] = {i: [] for i in ids}
        if include_employees:
            emps = (
                await self.session.execute(
                    select(Employee)
                    .where(Employee.department_id.in_(ids))
                    .order_by(Employee.full_name.asc(),
                              Employee.created_at.asc())
                )
            ).scalars().all()
            for e in emps:
                employees_map[e.department_id].append(e)

        def build(node_id: int) -> dict[str, Any]:
            d = dep_by_id[node_id]
            return {
                "department": d,
                "employees": employees_map.get(node_id, []),
                "children": [build(ch_id) for ch_id in sorted(children_map.get(
                    node_id, []
                    )) if ch_id != node_id],
            }

        return build(dep_id)

    async def _name_exists(self,
                           *,
                           name: str,
                           parent_id: int | None,
                           exclude_id: int | None = None) -> bool:
        stmt: Select[tuple[int]] = select(func.count(Department.id)).where(
            and_(
                func.coalesce(Department.parent_id,
                              0) == func.coalesce(parent_id, 0),
                Department.name == name,
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(Department.id != exclude_id)
        cnt = (await self.session.execute(stmt)).scalar_one()
        return cnt > 0

    async def _would_create_cycle(self,
                                  *,
                                  dep_id: int,
                                  new_parent_id: int) -> bool:
        current_id: int | None = new_parent_id
        while current_id is not None:
            if current_id == dep_id:
                return True
            current = await self.session.get(Department, current_id)
            if current is None:
                return False
            current_id = current.parent_id
        return False
