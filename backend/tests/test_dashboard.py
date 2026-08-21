"""Master dashboard, analytics, notifications, search and export.

These endpoints aggregate every other module, so they double as an
end-to-end check that a value entered in one place (an expense, a repayment,
a goal) actually shows up in the summary screens that are supposed to reflect
it - not a hardcoded or stale number.
"""

from __future__ import annotations

from datetime import date

DASHBOARD = "/api/v1/dashboard"
ANALYTICS = "/api/v1/analytics"
NOTIFICATIONS = "/api/v1/notifications"
SEARCH = "/api/v1/search"
EXPORT = "/api/v1/export"
LEDGER = "/api/v1/bahi-khata"


def test_dashboard_reflects_real_ledger_totals(alice):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Parbhu", "direction": "given", "purpose": "Trip", "amount": 12000},
    )
    dashboard = alice.get(DASHBOARD).json()

    assert dashboard["snapshot"]["to_receive"] == 12000
    assert dashboard["greeting"]["greeting"]
    bahi_khata_card = next(c for c in dashboard["cards"] if c["module"] == "bahi_khata")
    assert "12,000" in bahi_khata_card["headline"] or "12000" in bahi_khata_card["headline"]


def test_dashboard_masks_financial_figures_when_locked(alice):
    alice.set_pin("6205")
    dashboard = alice.get(DASHBOARD).json()

    assert dashboard["snapshot"]["financial_locked"] is True
    assert dashboard["snapshot"]["monthly_income"] is None
    expense_card = next(c for c in dashboard["cards"] if c["module"] == "expenses")
    assert expense_card["locked"] is True


def test_dashboard_unlocks_financial_figures_after_pin(alice):
    alice.set_pin("6205")
    alice.unlock("6205")
    food = next(c for c in alice.get("/api/v1/categories").json() if c["name"] == "Food")
    alice.post("/api/v1/expenses", json={"amount": 500, "category_id": food["id"]})

    dashboard = alice.get(DASHBOARD).json()
    assert dashboard["snapshot"]["financial_locked"] is False
    assert dashboard["snapshot"]["monthly_expenses"] == 500


def test_analytics_overview_combines_modules(alice):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Rahul", "direction": "borrowed", "purpose": "Loan", "amount": 5000},
    )
    alice.post("/api/v1/goals", json={"title": "Trek all Himalayan peaks"})

    overview = alice.get(ANALYTICS).json()
    assert overview["bahi_khata"]["total_borrowed"] == 5000
    # No Green PIN configured yet -> financial data is open (opt-in protection).
    assert overview["financial_locked"] is False
    assert overview["financial"] is not None
    assert overview["life"]["goals_in_progress"] == 1


def test_notifications_refresh_flags_overdue_ledger_entry(alice):
    from datetime import timedelta

    past = (date.today() - timedelta(days=3)).isoformat()
    alice.post(
        f"{LEDGER}/entries",
        json={
            "person_name": "Narayan Dai", "direction": "given", "purpose": "Emergency",
            "amount": 3000, "due_date": past,
        },
    )
    refreshed = alice.post(f"{NOTIFICATIONS}/refresh")
    assert refreshed.status_code == 200

    notifications = alice.get(NOTIFICATIONS).json()
    assert any(n["notification_type"] == "ledger_due" for n in notifications)

    unread = alice.get(f"{NOTIFICATIONS}/unread-count").json()
    assert unread["count"] >= 1

    first_id = notifications[0]["id"]
    marked = alice.post(f"{NOTIFICATIONS}/{first_id}/read")
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True


def test_custom_notification_can_be_created_and_dismissed(alice):
    created = alice.post(
        NOTIFICATIONS, json={"title": "Renew passport", "notification_type": "custom"}
    )
    assert created.status_code == 201
    notif_id = created.json()["id"]

    dismissed = alice.delete(f"{NOTIFICATIONS}/{notif_id}")
    assert dismissed.status_code == 200

    remaining = alice.get(NOTIFICATIONS).json()
    assert all(n["id"] != notif_id for n in remaining)


def test_global_search_finds_across_modules(alice):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Parbhu", "direction": "given", "purpose": "Tungnath trip", "amount": 1000},
    )
    alice.post("/api/v1/goals", json={"title": "Tungnath pilgrimage"})

    results = alice.get(SEARCH, params={"q": "Tungnath"}).json()["results"]
    types = {r["type"] for r in results}
    assert "ledger_entry" in types
    assert "life_goal" in types


def test_search_requires_minimum_query_length(alice):
    response = alice.get(SEARCH, params={"q": "a"})
    assert response.status_code == 200
    assert response.json()["results"] == []


def test_export_requires_green_pin_unlock(alice):
    alice.set_pin("9081")
    response = alice.get(f"{EXPORT}/json")
    assert response.status_code == 423


def test_export_json_contains_real_data(alice):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Parbhu", "direction": "given", "purpose": "Tungnath", "amount": 12000},
    )
    response = alice.get(f"{EXPORT}/json")
    assert response.status_code == 200
    body = response.json() if response.headers["content-type"].startswith("application/json") else None
    import json as _json

    body = _json.loads(response.content)
    assert body["bahi_khata"]["entries"][0]["purpose"] == "Tungnath"


def test_export_csv_returns_a_zip(alice):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Parbhu", "direction": "given", "purpose": "Tungnath", "amount": 12000},
    )
    response = alice.get(f"{EXPORT}/csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    import io
    import zipfile

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert "bahi_khata_entries.csv" in archive.namelist()


# --- Cross-user isolation -------------------------------------------------


def test_dashboard_and_search_are_isolated_per_user(alice, bob):
    alice.post(
        f"{LEDGER}/entries",
        json={"person_name": "Parbhu", "direction": "given", "purpose": "Secret Trip", "amount": 9999},
    )

    bob_dashboard = bob.get(DASHBOARD).json()
    assert bob_dashboard["snapshot"]["to_receive"] == 0

    bob_results = bob.get(SEARCH, params={"q": "Secret"}).json()["results"]
    assert bob_results == []
