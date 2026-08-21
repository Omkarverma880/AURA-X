"""Life goals and milestones.

Not confidential in the financial sense - progress toward "visit all 12
Jyotirlingas" is meant to be shown proudly - so this router sits outside the
Green PIN gate, unlike income and investments.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.core.deps import CurrentAuth, DbSession
from app.models.life import LifeGoalCategory
from app.schemas.common import MessageResponse
from app.schemas.life import (
    LifeCategoryCreate,
    LifeCategoryOut,
    LifeGoalCreate,
    LifeGoalDetail,
    LifeGoalOut,
    LifeGoalUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneUpdate,
)
from app.services import life as service
from app.services.ownership import owned_query

router = APIRouter(prefix="/goals", tags=["Life Goals"])


@router.get("/categories", response_model=list[LifeCategoryOut])
def list_categories(db: DbSession, ctx: CurrentAuth) -> list[LifeCategoryOut]:
    rows = db.execute(
        owned_query(LifeGoalCategory, ctx.user_id).order_by(LifeGoalCategory.sort_order)
    ).scalars()
    return [LifeCategoryOut.model_validate(r) for r in rows]


@router.post("/categories", response_model=LifeCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: LifeCategoryCreate, db: DbSession, ctx: CurrentAuth) -> LifeCategoryOut:
    category = LifeGoalCategory(user_id=ctx.user_id, **payload.model_dump())
    db.add(category)
    db.commit()
    return LifeCategoryOut.model_validate(category)


@router.get("", response_model=list[LifeGoalOut])
def list_goals(
    db: DbSession, ctx: CurrentAuth, status: str | None = None, category_id: uuid.UUID | None = None
) -> list[LifeGoalOut]:
    rows = service.list_goals(db, ctx.user_id, status=status, category_id=category_id)
    return [LifeGoalOut.model_validate(row) for row in rows]


@router.post("", response_model=LifeGoalDetail, status_code=status.HTTP_201_CREATED)
def create_goal(payload: LifeGoalCreate, db: DbSession, ctx: CurrentAuth) -> LifeGoalDetail:
    goal = service.create_goal(db, ctx.user_id, payload.model_dump())
    db.commit()
    return LifeGoalDetail.model_validate(service.get_goal_detail(db, ctx.user_id, goal.id))


@router.get("/{goal_id}", response_model=LifeGoalDetail)
def get_goal(goal_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> LifeGoalDetail:
    return LifeGoalDetail.model_validate(service.get_goal_detail(db, ctx.user_id, goal_id))


@router.patch("/{goal_id}", response_model=LifeGoalDetail)
def update_goal(
    goal_id: uuid.UUID, payload: LifeGoalUpdate, db: DbSession, ctx: CurrentAuth
) -> LifeGoalDetail:
    service.update_goal(db, ctx.user_id, goal_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return LifeGoalDetail.model_validate(service.get_goal_detail(db, ctx.user_id, goal_id))


@router.delete("/{goal_id}", response_model=MessageResponse)
def delete_goal(goal_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_goal(db, ctx.user_id, goal_id)
    db.commit()
    return MessageResponse(message="Goal deleted.")


@router.post(
    "/{goal_id}/milestones", response_model=LifeGoalDetail, status_code=status.HTTP_201_CREATED
)
def add_milestone(
    goal_id: uuid.UUID, payload: MilestoneCreate, db: DbSession, ctx: CurrentAuth
) -> LifeGoalDetail:
    service.add_milestone(db, ctx.user_id, goal_id, payload.model_dump())
    db.commit()
    return LifeGoalDetail.model_validate(service.get_goal_detail(db, ctx.user_id, goal_id))


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: uuid.UUID, payload: MilestoneUpdate, db: DbSession, ctx: CurrentAuth
) -> MilestoneOut:
    milestone = service.update_milestone(
        db, ctx.user_id, milestone_id, payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return MilestoneOut.model_validate(service.serialise_milestone(milestone))


@router.delete("/milestones/{milestone_id}", response_model=MessageResponse)
def delete_milestone(milestone_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_milestone(db, ctx.user_id, milestone_id)
    db.commit()
    return MessageResponse(message="Milestone removed.")
