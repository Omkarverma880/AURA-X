"""Expenditure management: categories, expenses, income and budgets.

Income is confidential, so every income/budget/monthly-summary test unlocks
the Green PIN first; the un-gated behaviour (423 while locked) is verified
explicitly in test_green_pin.py.
"""

from __future__ import annotations

from datetime import date

CATEGORIES = "/api/v1/categories"
EXPENSES = "/api/v1/expenses"
INCOME = "/api/v1/income"
BUDGETS = "/api/v1/budgets"

TODAY = date.today()
PERIOD = TODAY.replace(day=1).isoformat()


def food_category(alice):
    cats = alice.get(CATEGORIES).json()
    return next(c for c in cats if c["name"] == "Food")


def test_default_categories_are_seeded_on_registration(alice):
    response = alice.get(CATEGORIES)
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert {"Food", "Travel", "Bills", "Rent", "EMI"}.issubset(names)


def test_create_custom_category(alice):
    response = alice.post(CATEGORIES, json={"name": "Pet Care", "kind": "expense"})
    assert response.status_code == 201
    assert response.json()["name"] == "Pet Care"


def test_duplicate_category_name_is_rejected(alice):
    assert alice.post(CATEGORIES, json={"name": "Groceries"}).status_code == 201
    dup = alice.post(CATEGORIES, json={"name": "groceries"})
    assert dup.status_code == 409


def test_create_expense_and_read_it_back(alice):
    category = food_category(alice)
    response = alice.post(
        EXPENSES,
        json={
            "spent_on": TODAY.isoformat(),
            "amount": 450.50,
            "category_id": category["id"],
            "merchant": "Zomato",
            "payment_method": "upi",
            "description": "Dinner",
        },
    )
    assert response.status_code == 201
    expense = response.json()
    assert expense["amount"] == 450.50
    assert expense["category_name"] == "Food"

    fetched = alice.get(f"{EXPENSES}/{expense['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["merchant"] == "Zomato"


def test_expense_cannot_use_another_users_category(alice, bob):
    bob_category = food_category(bob)
    response = alice.post(
        EXPENSES, json={"amount": 100, "category_id": bob_category["id"], "spent_on": TODAY.isoformat()}
    )
    # Reported as not-found, not forbidden: existence of another user's row is
    # never confirmed to the caller.
    assert response.status_code == 404


def test_expense_list_filters_by_category_and_search(alice):
    food = food_category(alice)
    alice.post(EXPENSES, json={"amount": 200, "category_id": food["id"], "description": "Lunch"})
    alice.post(EXPENSES, json={"amount": 300, "description": "Movie tickets"})

    by_category = alice.get(EXPENSES, params={"category_id": food["id"]}).json()
    assert by_category["total"] == 1
    assert by_category["items"][0]["description"] == "Lunch"

    searched = alice.get(EXPENSES, params={"search": "Movie"}).json()
    assert searched["total"] == 1


def test_deleting_category_in_use_archives_instead_of_removing(alice):
    category = food_category(alice)
    alice.post(EXPENSES, json={"amount": 100, "category_id": category["id"]})

    response = alice.delete(f"{CATEGORIES}/{category['id']}")
    assert response.status_code == 200

    # Archived categories are hidden from the default listing (it feeds
    # dropdowns), so they must be asked for explicitly.
    remaining = alice.get(CATEGORIES, params={"include_archived": True}).json()
    archived = next(c for c in remaining if c["id"] == category["id"])
    assert archived["is_archived"] is True


def test_deleting_unused_category_removes_it(alice):
    created = alice.post(CATEGORIES, json={"name": "Unused"}).json()
    response = alice.delete(f"{CATEGORIES}/{created['id']}")
    assert response.status_code == 200
    remaining_ids = {c["id"] for c in alice.get(CATEGORIES).json()}
    assert created["id"] not in remaining_ids


# --- Income (Green PIN gated) -------------------------------------------


def test_income_is_locked_without_green_pin_unlock(alice):
    alice.set_pin("1357")
    response = alice.get(INCOME)
    assert response.status_code == 423
    assert response.json()["error"]["code"] == "financial_locked"


def test_income_is_open_when_no_pin_has_been_configured(alice):
    # A user who never set up a Green PIN has not opted into the gate.
    response = alice.get(INCOME)
    assert response.status_code == 200


def test_record_income_after_unlock(alice):
    alice.set_pin("1357")
    alice.unlock("1357")

    source = alice.post(
        f"{INCOME}/sources", json={"name": "Day Job", "income_type": "salary"}
    ).json()
    response = alice.post(
        INCOME,
        json={
            "source_id": source["id"],
            "received_on": TODAY.isoformat(),
            "gross_amount": 150000,
            "net_amount": 125000,
        },
    )
    assert response.status_code == 201
    record = response.json()
    assert record["net_amount"] == 125000
    assert record["deductions"] == 25000


def test_net_income_cannot_exceed_gross(alice):
    alice.set_pin("1357")
    alice.unlock("1357")
    response = alice.post(INCOME, json={"gross_amount": 1000, "net_amount": 1500})
    assert response.status_code == 422


# --- Monthly summary and budgets -----------------------------------------


def test_monthly_summary_combines_income_and_expenses(alice):
    alice.set_pin("2468")
    alice.unlock("2468")

    food = food_category(alice)
    alice.post(EXPENSES, json={"amount": 5000, "category_id": food["id"], "spent_on": TODAY.isoformat()})
    alice.post(INCOME, json={"gross_amount": 100000, "net_amount": 90000, "received_on": TODAY.isoformat()})

    response = alice.get("/api/v1/expenses/monthly-summary", params={"period": PERIOD})
    assert response.status_code == 200
    summary = response.json()
    assert summary["income"] == 90000
    assert summary["expenses"] == 5000
    assert summary["savings"] == 85000
    assert summary["savings_rate"] == 94.4


def test_budget_status_reflects_actual_spend(alice):
    alice.set_pin("2468")
    alice.unlock("2468")
    food = food_category(alice)

    put = alice.put(
        BUDGETS, json={"category_id": food["id"], "period_month": PERIOD, "amount": 1000}
    )
    assert put.status_code == 200

    alice.post(EXPENSES, json={"amount": 900, "category_id": food["id"], "spent_on": TODAY.isoformat()})

    budgets = alice.get(BUDGETS, params={"period": PERIOD}).json()
    row = next(b for b in budgets if b["category_id"] == food["id"])
    assert row["spent"] == 900
    assert row["remaining"] == 100
    assert row["status"] == "warning"


def test_budget_exceeded_status(alice):
    alice.set_pin("2468")
    alice.unlock("2468")
    food = food_category(alice)
    alice.put(BUDGETS, json={"category_id": food["id"], "period_month": PERIOD, "amount": 500})
    alice.post(EXPENSES, json={"amount": 700, "category_id": food["id"], "spent_on": TODAY.isoformat()})

    budgets = alice.get(BUDGETS, params={"period": PERIOD}).json()
    row = next(b for b in budgets if b["category_id"] == food["id"])
    assert row["status"] == "exceeded"
    assert row["remaining"] == -200


def test_cross_user_expense_isolation(alice, bob):
    """The mandatory cross-tenant check: bob must never reach alice's data."""
    food = food_category(alice)
    created = alice.post(
        EXPENSES, json={"amount": 999, "category_id": food["id"], "description": "Alice only"}
    ).json()

    # Same id, different owner - reported as not found either way.
    assert bob.get(f"{EXPENSES}/{created['id']}").status_code == 404
    assert bob.patch(f"{EXPENSES}/{created['id']}", json={"amount": 1}).status_code == 404
    assert bob.delete(f"{EXPENSES}/{created['id']}").status_code == 404

    bob_list = bob.get(EXPENSES).json()
    assert bob_list["total"] == 0


def test_cross_user_income_isolation(alice, bob):
    alice.set_pin("7391")
    alice.unlock("7391")
    bob.set_pin("8642")
    bob.unlock("8642")

    record = alice.post(INCOME, json={"gross_amount": 50000, "net_amount": 45000}).json()

    assert bob.get(INCOME).json()["total"] == 0
    assert bob.patch(f"{INCOME}/{record['id']}", json={"gross_amount": 1}).status_code == 404
    assert bob.delete(f"{INCOME}/{record['id']}").status_code == 404
