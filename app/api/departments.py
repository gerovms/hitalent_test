from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.schemas.department import (DepartmentCreate, DepartmentOut,
                                    DepartmentTree, DepartmentUpdate)
from app.schemas.employee import EmployeeCreate, EmployeeOut
from app.services.department_service import DepartmentService
from app.services.employee_service import EmployeeService

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("/",
             response_model=DepartmentOut,
             status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    session: AsyncSession = Depends(get_session)
) -> DepartmentOut:
    service = DepartmentService(session)
    try:
        dep = await service.create(name=payload.name,
                                   parent_id=payload.parent_id)
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return DepartmentOut.model_validate(dep)


@router.post("/{dep_id}/employees/",
             response_model=EmployeeOut,
             status_code=status.HTTP_201_CREATED)
async def create_employee(
    dep_id: int,
    payload: EmployeeCreate,
    session: AsyncSession = Depends(get_session),
) -> EmployeeOut:
    service = EmployeeService(session)
    try:
        emp = await service.create(
            dep_id,
            full_name=payload.full_name,
            position=payload.position,
            hired_at=payload.hired_at,
        )
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return EmployeeOut.model_validate(emp)


@router.get("/{dep_id}", response_model=DepartmentTree)
async def get_department(
    dep_id: int,
    depth: int = Query(default=1, ge=1, le=5),
    include_employees: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
) -> DepartmentTree:
    service = DepartmentService(session)
    try:
        tree = await service.get_tree(dep_id,
                                      depth=depth,
                                      include_employees=include_employees)
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    return DepartmentTree(
        department=DepartmentOut.model_validate(tree["department"]),
        employees=[EmployeeOut.model_validate(e) for e in tree["employees"]],
        children=[
            _tree_to_schema(ch) for ch in tree["children"]
        ],
    )


def _tree_to_schema(node) -> DepartmentTree:
    return DepartmentTree(
        department=DepartmentOut.model_validate(node["department"]),
        employees=[EmployeeOut.model_validate(e) for e in node["employees"]],
        children=[_tree_to_schema(ch) for ch in node["children"]],
    )


@router.patch("/{dep_id}", response_model=DepartmentOut)
async def patch_department(
    dep_id: int,
    payload: DepartmentUpdate,
    session: AsyncSession = Depends(get_session),
) -> DepartmentOut:
    service = DepartmentService(session)
    try:
        dep = await service.update(dep_id,
                                   name=payload.name,
                                   parent_id=payload.parent_id)
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return DepartmentOut.model_validate(dep)


@router.delete("/{dep_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dep_id: int,
    mode: str = Query(default="cascade", pattern="^(cascade|reassign)$"),
    reassign_to_department_id: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> Response:
    service = DepartmentService(session)
    try:
        await service.delete(
            dep_id,
            mode=mode,
            reassign_to_department_id=reassign_to_department_id
            )
    except KeyError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
