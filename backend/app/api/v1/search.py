"""Global search across every module.

A single lightweight endpoint rather than a search index: personal data at
this scale (hundreds to low thousands of rows) does not need Elasticsearch,
and every query is already scoped to the caller by owned_query.
"""

from __future__ import annotations

from sqlalchemy import or_, select

from fastapi import APIRouter

from app.core.deps import CurrentAuth, DbSession
from app.models.finance import Expense
from app.models.investment import InvestmentHolding
from app.models.ledger import LedgerEntry, Person
from app.models.life import Checklist, LifeGoal
from app.models.memories import Album
from app.services.ownership import owned_query

router = APIRouter(prefix="/search", tags=["Search"])

MAX_PER_TYPE = 5


@router.get("")
def global_search(q: str, db: DbSession, ctx: CurrentAuth) -> dict:
    query = q.strip()
    if len(query) < 2:
        return {"query": query, "results": []}

    pattern = f"%{query}%"
    results: list[dict] = []

    for person in db.execute(
        owned_query(Person, ctx.user_id).where(Person.name.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {"type": "person", "id": str(person.id), "title": person.name, "subtitle": person.relation}
        )

    for entry in db.execute(
        owned_query(LedgerEntry, ctx.user_id).where(LedgerEntry.purpose.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {
                "type": "ledger_entry",
                "id": str(entry.id),
                "title": entry.purpose,
                "subtitle": f"{entry.direction} · {entry.entry_date}",
            }
        )

    for expense in db.execute(
        owned_query(Expense, ctx.user_id)
        .where(or_(Expense.description.ilike(pattern), Expense.merchant.ilike(pattern)))
        .limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {
                "type": "expense",
                "id": str(expense.id),
                "title": expense.description or expense.merchant or "Expense",
                "subtitle": str(expense.spent_on),
            }
        )

    for holding in db.execute(
        owned_query(InvestmentHolding, ctx.user_id).where(InvestmentHolding.name.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {
                "type": "investment",
                "id": str(holding.id),
                "title": holding.name,
                "subtitle": holding.asset_type,
            }
        )

    for goal in db.execute(
        owned_query(LifeGoal, ctx.user_id).where(LifeGoal.title.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append({"type": "life_goal", "id": str(goal.id), "title": goal.title, "subtitle": goal.status})

    for checklist in db.execute(
        owned_query(Checklist, ctx.user_id).where(Checklist.title.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {"type": "checklist", "id": str(checklist.id), "title": checklist.title, "subtitle": checklist.tracker_type}
        )

    for album in db.execute(
        owned_query(Album, ctx.user_id).where(Album.title.ilike(pattern)).limit(MAX_PER_TYPE)
    ).scalars():
        results.append(
            {"type": "album", "id": str(album.id), "title": album.title, "subtitle": album.location}
        )

    return {"query": query, "results": results}
