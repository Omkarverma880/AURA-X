"""Settling money against a person instead of a specific loan.

The bahi khata mental model: you remember that Rahul handed back 500, not
which of his three loans it belonged to.
"""

from __future__ import annotations

BASE = "/api/v1/bahi-khata"


def lend(alice, amount, purpose, name="Rahul Bhaiya", **extra):
    response = alice.post(
        f"{BASE}/entries",
        json={
            "person_name": name,
            "direction": "given",
            "purpose": purpose,
            "amount": amount,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def pay(alice, person_id, amount, **extra):
    return alice.post(
        f"{BASE}/people/{person_id}/payments", json={"amount": amount, **extra}
    )


def test_a_payment_clears_the_oldest_debt_first(alice):
    first = lend(alice, 1000, "Old loan", entry_date="2026-01-10")
    second = lend(alice, 5000, "Newer loan", entry_date="2026-03-01")
    person_id = first["person_id"]

    response = pay(alice, person_id, 1500)
    assert response.status_code == 201, response.text

    assert alice.get(f"{BASE}/entries/{first['id']}").json()["outstanding"] == 0
    assert alice.get(f"{BASE}/entries/{second['id']}").json()["outstanding"] == 4500


def test_the_users_own_scenario(alice):
    """Gave 2,000 then 5,000; got back 500, 500 and 1,000 on separate days."""
    lend(alice, 2000, "First", entry_date="2026-01-05")
    lend(alice, 5000, "Second", entry_date="2026-02-05")
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]

    for amount in (500, 500, 1000):
        assert pay(alice, person_id, amount).status_code == 201

    person = alice.get(f"{BASE}/people/{person_id}").json()
    assert person["total_given"] == 7000
    assert person["total_received"] == 2000
    assert person["outstanding_receivable"] == 5000


def test_a_payment_splits_across_entries_and_records_both_legs(alice):
    """One payment covering two loans must leave a trail on each, not one
    lumped row - otherwise the per-entry history lies."""
    lend(alice, 1000, "Old", entry_date="2026-01-10")
    lend(alice, 5000, "New", entry_date="2026-03-01")
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]

    pay(alice, person_id, 1500)

    ledger = alice.get(f"{BASE}/people/{person_id}").json()["ledger"]
    repayments = sorted(t["amount"] for t in ledger if t["txn_type"] == "repayment")
    assert repayments == [500, 1000]


def test_paying_more_than_is_owed_is_refused(alice):
    lend(alice, 1000, "Only loan")
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]

    response = pay(alice, person_id, 2500)
    assert response.status_code == 400
    assert "more than" in response.json()["error"]["message"].lower()


def test_paying_a_person_who_owes_nothing_is_refused(alice):
    lend(alice, 1000, "Loan")
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]
    pay(alice, person_id, 1000)

    response = pay(alice, person_id, 100)
    assert response.status_code == 400


def test_borrowed_money_is_settled_separately_from_lent_money(alice):
    """A person you both lent to and borrowed from must not have one side
    accidentally settle the other."""
    lend(alice, 3000, "I lent")
    alice.post(
        f"{BASE}/entries",
        json={
            "person_name": "Rahul Bhaiya",
            "direction": "borrowed",
            "purpose": "I borrowed",
            "amount": 2000,
        },
    )
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]

    assert pay(alice, person_id, 500, direction="borrowed").status_code == 201

    person = alice.get(f"{BASE}/people/{person_id}").json()
    assert person["outstanding_receivable"] == 3000   # untouched
    assert person["outstanding_payable"] == 1500      # reduced


def test_another_users_person_cannot_be_paid(alice, bob):
    lend(alice, 1000, "Loan")
    person_id = alice.get(f"{BASE}/people").json()[0]["id"]

    assert pay(bob, person_id, 100).status_code == 404
