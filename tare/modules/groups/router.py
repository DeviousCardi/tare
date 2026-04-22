"""Routes for groups."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.groups.schemas import (
    GroupOut, JoinGroup, LeaveGroup, ListGroups, MembershipOut, OpenGroup,
)
from tare.modules.groups.service import GroupsService

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("")
def list_groups(
    operator: TheOperator, store: TheStore,
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = GroupsService(store).list(operator, ListGroups(limit=limit, offset=offset))
    return {"data": [GroupOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/together")
def belong_together(
    one: str, other: str, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"one": one, "other": other, "on": on,
            "together": GroupsService(store).belong_together(operator, one, other, on)}


@router.get("/of/{employer_id}")
def groups_for(
    employer_id: str, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"employer_id": employer_id,
            "groups": GroupsService(store).groups_for(operator, employer_id, on)}


@router.get("/{group_id}")
def get_group(group_id: str, operator: TheOperator, store: TheStore) -> GroupOut:
    return GroupOut.of(GroupsService(store).get(operator, group_id))


@router.get("/{group_id}/members")
def group_members(
    group_id: str, on: str, operator: TheOperator, store: TheStore,
) -> dict:
    return {"group_id": group_id,
            "members": GroupsService(store).members(operator, group_id, on)}


@router.post("", status_code=201)
def open_group(dto: OpenGroup, operator: TheOperator, store: TheStore) -> GroupOut:
    return GroupOut.of(GroupsService(store).open(operator, dto))


@router.post("/join", status_code=201)
def join_group(dto: JoinGroup, operator: TheOperator, store: TheStore) -> MembershipOut:
    return MembershipOut.of(GroupsService(store).join(operator, dto))


@router.post("/membership/{membership_id}/leave")
def leave_group(
    membership_id: str, dto: LeaveGroup, operator: TheOperator, store: TheStore,
) -> MembershipOut:
    return MembershipOut.of(GroupsService(store).leave(operator, membership_id, dto))
