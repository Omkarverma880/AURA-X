"""Bahi Khata endpoints.

Note the shape of every handler: the entity id arrives from the URL, but the
owner always comes from ctx.user_id. A caller cannot reach another ledger by
editing an id.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentAuth, DbSession
from app.schemas.common import MessageResponse, Page
from app.schemas.ledger import (
    EntryCreate,
    EntryDetail,
    EntryOut,
    EntryUpdate,
    LedgerAnalytics,
    LedgerSummary,
    PersonCreate,
    PersonDetail,
    PersonPaymentCreate,
    PersonOut,
    PersonUpdate,
    TransactionCreate,
    TransactionOut,
    VoidRequest,
)
from app.services import ledger as service

router = APIRouter(prefix="/bahi-khata", tags=["Bahi Khata"])


# --- People ------------------------------------------------------------


@router.get("/people", response_model=list[PersonOut])
def list_people(
    db: DbSession,
    ctx: CurrentAuth,
    search: str | None = None,
    include_archived: bool = False,
    only_outstanding: bool = False,
) -> list[PersonOut]:
    rows = service.list_people(
        db,
        ctx.user_id,
        search=search,
        include_archived=include_archived,
        only_outstanding=only_outstanding,
    )
    return [PersonOut.model_validate(row) for row in rows]


@router.post("/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: DbSession, ctx: CurrentAuth) -> PersonOut:
    person = service.create_person(db, ctx.user_id, payload.model_dump())
    db.commit()
    return PersonOut.model_validate(service.person_base(person))


@router.get("/people/{person_id}", response_model=PersonDetail)
def get_person(person_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> PersonDetail:
    return PersonDetail.model_validate(service.get_person_detail(db, ctx.user_id, person_id))


@router.patch("/people/{person_id}", response_model=PersonOut)
def update_person(
    person_id: uuid.UUID, payload: PersonUpdate, db: DbSession, ctx: CurrentAuth
) -> PersonOut:
    person = service.update_person(
        db, ctx.user_id, person_id, payload.model_dump(exclude_unset=True)
    )
    db.commit()
    return PersonOut.model_validate(service.person_base(person))


@router.delete("/people/{person_id}", response_model=MessageResponse)
def delete_person(person_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_person(db, ctx.user_id, person_id)
    db.commit()
    return MessageResponse(message="Person removed from your Bahi Khata.")


# --- Entries -----------------------------------------------------------


@router.post(
    "/people/{person_id}/payments",
    response_model=PersonDetail,
    status_code=status.HTTP_201_CREATED,
)
def record_person_payment(
    person_id: uuid.UUID,
    payload: PersonPaymentCreate,
    db: DbSession,
    ctx: CurrentAuth,
) -> PersonDetail:
    """Settle money against a person, without naming a specific entry.

    The amount is applied to that person's open entries oldest first - the way
    a running khata works - so the caller only has to know who paid and how
    much.
    """
    service.record_person_payment(db, ctx.user_id, person_id, payload.model_dump())
    db.commit()
    return PersonDetail.model_validate(
        service.get_person_detail(db, ctx.user_id, person_id)
    )


@router.get("/entries", response_model=Page[EntryOut])
def list_entries(
    db: DbSession,
    ctx: CurrentAuth,
    direction: str | None = None,
    entry_status: str | None = Query(default=None, alias="status"),
    person_id: uuid.UUID | None = None,
    search: str | None = None,
    sort: str = "recent",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
) -> Page[EntryOut]:
    items, total = service.list_entries(
        db,
        ctx.user_id,
        direction=direction,
        status=entry_status,
        person_id=person_id,
        search=search,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return Page[EntryOut](
        items=[EntryOut.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/entries", response_model=EntryDetail, status_code=status.HTTP_201_CREATED)
def create_entry(payload: EntryCreate, db: DbSession, ctx: CurrentAuth) -> EntryDetail:
    entry = service.create_entry(db, ctx.user_id, payload.model_dump())
    db.commit()
    return EntryDetail.model_validate(service.get_entry_detail(db, ctx.user_id, entry.id))


@router.get("/entries/{entry_id}", response_model=EntryDetail)
def get_entry(entry_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> EntryDetail:
    return EntryDetail.model_validate(service.get_entry_detail(db, ctx.user_id, entry_id))


@router.patch("/entries/{entry_id}", response_model=EntryDetail)
def update_entry(
    entry_id: uuid.UUID, payload: EntryUpdate, db: DbSession, ctx: CurrentAuth
) -> EntryDetail:
    service.update_entry(db, ctx.user_id, entry_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return EntryDetail.model_validate(service.get_entry_detail(db, ctx.user_id, entry_id))


@router.delete("/entries/{entry_id}", response_model=MessageResponse)
def delete_entry(entry_id: uuid.UUID, db: DbSession, ctx: CurrentAuth) -> MessageResponse:
    service.delete_entry(db, ctx.user_id, entry_id)
    db.commit()
    return MessageResponse(message="Entry deleted.")


# --- Transactions ------------------------------------------------------


@router.post(
    "/entries/{entry_id}/transactions",
    response_model=EntryDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_transaction(
    entry_id: uuid.UUID, payload: TransactionCreate, db: DbSession, ctx: CurrentAuth
) -> EntryDetail:
    """Record a repayment, extra principal, interest or write-off."""
    service.add_transaction(db, ctx.user_id, entry_id, payload.model_dump())
    db.commit()
    return EntryDetail.model_validate(service.get_entry_detail(db, ctx.user_id, entry_id))


@router.post("/entries/{entry_id}/settle", response_model=EntryDetail)
def settle_entry(
    entry_id: uuid.UUID, db: DbSession, ctx: CurrentAuth, payload: TransactionCreate | None = None
) -> EntryDetail:
    """Clear whatever is still outstanding and close the entry."""
    service.settle_entry(db, ctx.user_id, entry_id, payload.model_dump() if payload else {})
    db.commit()
    return EntryDetail.model_validate(service.get_entry_detail(db, ctx.user_id, entry_id))


@router.post("/transactions/{txn_id}/void", response_model=TransactionOut)
def void_transaction(
    txn_id: uuid.UUID, payload: VoidRequest, db: DbSession, ctx: CurrentAuth
) -> TransactionOut:
    """Reverse a transaction while keeping it visible in the history."""
    txn = service.void_transaction(db, ctx.user_id, txn_id, payload.reason)
    db.commit()
    return TransactionOut.model_validate(service.serialise_txn(txn, None))


# --- Analytics ---------------------------------------------------------


@router.get("/summary", response_model=LedgerSummary)
def summary(db: DbSession, ctx: CurrentAuth) -> LedgerSummary:
    return LedgerSummary.model_validate(service.get_summary(db, ctx.user_id))


@router.get("/analytics", response_model=LedgerAnalytics)
def analytics(db: DbSession, ctx: CurrentAuth, months: int = 12) -> LedgerAnalytics:
    return LedgerAnalytics.model_validate(service.get_analytics(db, ctx.user_id, months))
