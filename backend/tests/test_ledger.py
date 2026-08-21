"""Bahi Khata behaviour: balances, settlement and immutable history."""

from __future__ import annotations

from datetime import date, timedelta

BASE = "/api/v1/bahi-khata"


def make_entry(user, *, name="Parbhu", amount=12000, direction="given", purpose="Tungnath", **extra):
    payload = {
        "person_name": name,
        "direction": direction,
        "purpose": purpose,
        "amount": amount,
        **extra,
    }
    response = user.post(f"{BASE}/entries", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_creating_an_entry_posts_its_principal(alice):
    entry = make_entry(alice, amount=12000)

    assert entry["principal_amount"] == 12000
    assert entry["settled_amount"] == 0
    assert entry["outstanding"] == 12000
    assert entry["status"] == "active"
    # The opening principal is itself a transaction, not a stored balance.
    assert len(entry["transactions"]) == 1
    assert entry["transactions"][0]["txn_type"] == "principal"


def test_partial_repayment_moves_entry_to_partial(alice):
    entry = make_entry(alice, amount=12000)
    response = alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 5000},
    )
    assert response.status_code == 201
    updated = response.json()

    assert updated["settled_amount"] == 5000
    assert updated["outstanding"] == 7000
    assert updated["status"] == "partial"
    assert updated["progress_percent"] == 41.7


def test_full_repayment_settles_the_entry(alice):
    entry = make_entry(alice, amount=12000)
    alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 12000},
    )
    detail = alice.get(f"{BASE}/entries/{entry['id']}").json()

    assert detail["outstanding"] == 0
    assert detail["status"] == "settled"


def test_repayment_cannot_exceed_outstanding(alice):
    entry = make_entry(alice, amount=1000)
    response = alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 1500},
    )
    assert response.status_code == 400
    assert "outstanding" in response.json()["error"]["message"].lower()


def test_settle_endpoint_clears_the_remainder(alice):
    entry = make_entry(alice, amount=8000)
    alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 3000},
    )
    response = alice.post(f"{BASE}/entries/{entry['id']}/settle")
    assert response.status_code == 200
    settled = response.json()
    assert settled["outstanding"] == 0
    assert settled["status"] == "settled"
    assert settled["is_closed"] is True


def test_void_keeps_history_and_restores_the_balance(alice):
    entry = make_entry(alice, amount=10000)
    detail = alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 4000},
    ).json()
    repayment = next(t for t in detail["transactions"] if t["txn_type"] == "repayment")

    response = alice.post(
        f"{BASE}/transactions/{repayment['id']}/void", json={"reason": "Entered twice"}
    )
    assert response.status_code == 200

    after = alice.get(f"{BASE}/entries/{entry['id']}").json()
    assert after["outstanding"] == 10000
    # The voided row is still part of the record.
    voided = next(t for t in after["transactions"] if t["id"] == repayment["id"])
    assert voided["is_voided"] is True
    assert voided["void_reason"] == "Entered twice"


def test_void_cannot_be_applied_twice(alice):
    entry = make_entry(alice, amount=5000)
    detail = alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 1000},
    ).json()
    txn = next(t for t in detail["transactions"] if t["txn_type"] == "repayment")

    assert alice.post(f"{BASE}/transactions/{txn['id']}/void", json={"reason": "one"}).status_code == 200
    assert alice.post(f"{BASE}/transactions/{txn['id']}/void", json={"reason": "two"}).status_code == 400


def test_running_balance_is_chronological(alice):
    entry = make_entry(alice, amount=10000)
    for amount in (2000, 3000):
        alice.post(
            f"{BASE}/entries/{entry['id']}/transactions",
            json={"txn_type": "repayment", "amount": amount},
        )

    detail = alice.get(f"{BASE}/entries/{entry['id']}").json()
    # Newest first in the response; oldest first for the running balance.
    balances = [t["balance_after"] for t in reversed(detail["transactions"])]
    assert balances == [10000, 8000, 5000]


def test_overdue_entry_is_flagged(alice):
    past = (date.today() - timedelta(days=10)).isoformat()
    entry = make_entry(alice, amount=4000, due_date=past)
    listing = alice.get(f"{BASE}/entries").json()
    row = next(item for item in listing["items"] if item["id"] == entry["id"])

    assert row["status"] == "overdue"
    assert row["is_overdue"] is True
    assert row["days_overdue"] == 10


def test_borrowed_entries_track_payable_separately(alice):
    make_entry(alice, name="Parbhu", amount=12000, direction="given")
    make_entry(alice, name="Rahul", amount=20000, direction="borrowed", purpose="Emergency")
    borrowed = alice.get(f"{BASE}/entries", params={"direction": "borrowed"}).json()["items"][0]
    alice.post(
        f"{BASE}/entries/{borrowed['id']}/transactions",
        json={"txn_type": "repayment", "amount": 5000},
    )

    summary = alice.get(f"{BASE}/summary").json()
    assert summary["total_given"] == 12000
    assert summary["outstanding_receivable"] == 12000
    assert summary["total_borrowed"] == 20000
    assert summary["total_repaid"] == 5000
    assert summary["outstanding_payable"] == 15000
    assert summary["net_position"] == -3000


def test_person_profile_aggregates_every_entry(alice):
    make_entry(alice, name="Parbhu", amount=12000, purpose="Tungnath")
    make_entry(alice, name="Parbhu", amount=54592, purpose="Loan")

    person = alice.get(f"{BASE}/people").json()[0]
    detail = alice.get(f"{BASE}/people/{person['id']}").json()

    assert detail["name"] == "Parbhu"
    assert detail["total_given"] == 66592
    assert detail["total_received"] == 0
    assert detail["outstanding_receivable"] == 66592
    assert detail["entry_count"] == 2
    assert detail["active_count"] == 2
    assert len(detail["ledger"]) == 2


def test_people_list_reports_derived_totals(alice):
    make_entry(alice, name="Narayan Dai", amount=9000)
    entry = alice.get(f"{BASE}/entries").json()["items"][0]
    alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 2500},
    )

    person = alice.get(f"{BASE}/people").json()[0]
    assert person["total_given"] == 9000
    assert person["total_received"] == 2500
    assert person["outstanding_receivable"] == 6500
    assert person["net_balance"] == 6500


def test_duplicate_person_name_is_rejected(alice):
    assert alice.post(f"{BASE}/people", json={"name": "Parbhu"}).status_code == 201
    duplicate = alice.post(f"{BASE}/people", json={"name": "parbhu"})
    assert duplicate.status_code == 409


def test_person_with_outstanding_balance_cannot_be_deleted(alice):
    make_entry(alice, name="Parbhu", amount=1000)
    person = alice.get(f"{BASE}/people").json()[0]

    blocked = alice.delete(f"{BASE}/people/{person['id']}")
    assert blocked.status_code == 400

    entry = alice.get(f"{BASE}/entries").json()["items"][0]
    alice.post(f"{BASE}/entries/{entry['id']}/settle")
    assert alice.delete(f"{BASE}/people/{person['id']}").status_code == 200


def test_filters_and_search(alice):
    make_entry(alice, name="Parbhu", amount=12000, purpose="Tungnath")
    make_entry(alice, name="Rahul", amount=20000, direction="borrowed", purpose="Emergency")

    given = alice.get(f"{BASE}/entries", params={"direction": "given"}).json()
    assert given["total"] == 1
    assert given["items"][0]["person_name"] == "Parbhu"

    searched = alice.get(f"{BASE}/entries", params={"search": "Emergen"}).json()
    assert searched["total"] == 1
    assert searched["items"][0]["direction"] == "borrowed"


def test_analytics_reports_trend_and_breakdown(alice):
    make_entry(alice, name="Parbhu", amount=12000)
    entry = alice.get(f"{BASE}/entries").json()["items"][0]
    alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 2000},
    )

    analytics = alice.get(f"{BASE}/analytics").json()
    assert analytics["summary"]["outstanding_receivable"] == 10000
    assert analytics["summary"]["settlement_rate"] == 16.7
    assert analytics["monthly_trend"][-1]["given"] == 12000
    assert analytics["monthly_trend"][-1]["received"] == 2000
    assert analytics["outstanding_by_person"][0]["name"] == "Parbhu"


def test_amounts_keep_paisa_precision(alice):
    entry = make_entry(alice, amount=1000.55)
    detail = alice.post(
        f"{BASE}/entries/{entry['id']}/transactions",
        json={"txn_type": "repayment", "amount": 333.15},
    ).json()
    assert detail["outstanding"] == 667.40


def test_future_dated_entries_are_rejected(alice):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    response = alice.post(
        f"{BASE}/entries",
        json={
            "person_name": "Parbhu",
            "direction": "given",
            "purpose": "Advance",
            "amount": 500,
            "entry_date": tomorrow,
        },
    )
    assert response.status_code == 422


def test_negative_amounts_are_rejected(alice):
    response = alice.post(
        f"{BASE}/entries",
        json={"person_name": "X", "direction": "given", "purpose": "Bad", "amount": -100},
    )
    assert response.status_code == 422
