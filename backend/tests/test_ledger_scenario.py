"""The real-world repayment pattern: several loans, several part-payments."""

from __future__ import annotations

BASE = "/api/v1/bahi-khata"


def test_multiple_loans_and_partial_repayments_to_one_person(alice):
    """Gave 2,000 then 5,000; received 500 + 500 + 1,000.
    7,000 lent, 2,000 back, 5,000 still owed."""
    first = alice.post(
        f"{BASE}/entries",
        json={
            "person_name": "Rahul Bhaiya",
            "direction": "given",
            "purpose": "Loan",
            "amount": 2000,
        },
    ).json()
    second = alice.post(
        f"{BASE}/entries",
        json={
            "person_name": "Rahul Bhaiya",
            "direction": "given",
            "purpose": "Second loan",
            "amount": 5000,
        },
    ).json()

    for amount in (500, 500, 1000):
        response = alice.post(
            f"{BASE}/entries/{second['id']}/transactions",
            json={"txn_type": "repayment", "amount": amount},
        )
        assert response.status_code == 201, response.text

    detail = alice.get(f"{BASE}/entries/{second['id']}").json()
    assert detail["principal_amount"] == 5000
    assert detail["settled_amount"] == 2000
    assert detail["outstanding"] == 3000
    assert detail["status"] == "partial"

    # The untouched loan is unaffected.
    assert alice.get(f"{BASE}/entries/{first['id']}").json()["outstanding"] == 2000

    # And the person-level totals - what the Bahi Khata cards show.
    person_id = detail["person_id"]
    profile = alice.get(f"{BASE}/people/{person_id}").json()
    print("\nPERSON PROFILE:", {k: v for k, v in profile.items() if "total" in k or "net" in k})
    assert profile["total_given"] == 7000
    assert profile["total_received"] == 2000
