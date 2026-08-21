"""Life goals, custom checklists/trackers, and photo albums."""

from __future__ import annotations

import io

from PIL import Image

GOALS = "/api/v1/goals"
CHECKLISTS = "/api/v1/checklists"
MEMORIES = "/api/v1/memories"


def make_jpeg_bytes(size=(64, 64), color=(200, 30, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG")
    return buffer.getvalue()


# --- Life goals ------------------------------------------------------------


def test_create_life_goal_without_milestones_starts_at_zero_progress(alice):
    response = alice.post(
        GOALS, json={"title": "Complete 20 major treks", "priority": "high"}
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["progress_percent"] == 0
    assert goal["status"] == "in_progress"


def test_progress_is_derived_from_milestones(alice):
    goal = alice.post(GOALS, json={"title": "12 Jyotirlingas"}).json()
    for title in ["Somnath", "Kedarnath", "Kashi Vishwanath", "Omkareshwar"]:
        alice.post(f"{GOALS}/{goal['id']}/milestones", json={"title": title})

    detail = alice.get(f"{GOALS}/{goal['id']}").json()
    assert detail["milestone_total"] == 4
    milestone_id = detail["milestones"][0]["id"]

    alice.patch(f"{GOALS}/milestones/{milestone_id}", json={"is_completed": True})
    updated = alice.get(f"{GOALS}/{goal['id']}").json()
    assert updated["milestone_done"] == 1
    assert updated["progress_percent"] == 25.0


def test_progress_derived_from_target_amount_when_no_milestones(alice):
    goal = alice.post(
        GOALS,
        json={"title": "Build 1 crore corpus", "target_amount": 10000000, "current_amount": 2500000},
    ).json()
    assert goal["progress_percent"] == 25.0


def test_completing_a_goal_sets_completed_date(alice):
    goal = alice.post(GOALS, json={"title": "Visit Japan"}).json()
    updated = alice.patch(f"{GOALS}/{goal['id']}", json={"status": "completed"}).json()
    assert updated["status"] == "completed"
    assert updated["completed_on"] is not None


def test_overdue_goal_is_flagged(alice):
    from datetime import date, timedelta

    past = (date.today() - timedelta(days=5)).isoformat()
    goal = alice.post(GOALS, json={"title": "Late goal", "target_date": past}).json()
    listing = {g["id"]: g for g in alice.get(GOALS).json()}
    assert listing[goal["id"]]["is_overdue"] is True


# --- Custom checklists / trackers -----------------------------------------


def test_create_jyotirlinga_checklist_with_seeded_items(alice):
    response = alice.post(
        CHECKLISTS,
        json={
            "title": "12 Jyotirlingas",
            "tracker_type": "temple",
            "items": [
                "Somnath", "Mallikarjuna", "Mahakaleshwar", "Omkareshwar", "Kedarnath",
                "Bhimashankar", "Kashi Vishwanath", "Trimbakeshwar", "Vaidyanath",
                "Nageshwar", "Rameshwar", "Grishneshwar",
            ],
        },
    )
    assert response.status_code == 201
    checklist = response.json()
    assert checklist["item_count"] == 12
    assert checklist["completed_count"] == 0
    assert len(checklist["items"]) == 12


def test_completing_items_updates_progress(alice):
    checklist = alice.post(
        CHECKLISTS, json={"title": "Treks", "tracker_type": "trek", "target_count": 20}
    ).json()
    for name in ["Tungnath", "Kedarkantha", "Roopkund"]:
        alice.post(f"{CHECKLISTS}/{checklist['id']}/items", json={"name": name})

    detail = alice.get(f"{CHECKLISTS}/{checklist['id']}").json()
    item_id = detail["items"][0]["id"]
    alice.patch(f"{CHECKLISTS}/items/{item_id}", json={"is_completed": True, "rating": 5})

    updated = alice.get(f"{CHECKLISTS}/{checklist['id']}").json()
    assert updated["completed_count"] == 1
    # target_count=20 is the denominator, not the 3 items actually recorded.
    assert updated["progress_percent"] == 5.0
    completed_item = next(i for i in updated["items"] if i["is_completed"])
    assert completed_item["rating"] == 5


def test_custom_tracker_type_is_freeform(alice):
    response = alice.post(
        CHECKLISTS, json={"title": "Books I've Read 2026", "tracker_type": "book"}
    )
    assert response.status_code == 201
    item = alice.post(
        f"{CHECKLISTS}/{response.json()['id']}/items",
        json={"name": "Sapiens", "details": {"author": "Yuval Noah Harari"}},
    )
    assert item.status_code == 201


# --- Memories / albums -----------------------------------------------------


def test_create_album_and_upload_photo(alice):
    album = alice.post(
        MEMORIES + "/albums",
        json={"title": "Uttarakhand 4 Dham - 2026", "album_type": "trip", "location": "Uttarakhand"},
    ).json()

    files = {"file": ("trip.jpg", make_jpeg_bytes(), "image/jpeg")}
    uploaded = alice.post(
        f"{MEMORIES}/albums/{album['id']}/photos", files=files, data={"caption": "Kedarnath sunrise"}
    )
    assert uploaded.status_code == 201
    photo = uploaded.json()
    assert photo["url"]
    assert photo["thumbnail_url"]
    assert photo["caption"] == "Kedarnath sunrise"

    detail = alice.get(f"{MEMORIES}/albums/{album['id']}").json()
    assert detail["photo_count"] == 1
    # First photo becomes the cover automatically.
    assert detail["cover_photo_id"] == photo["id"]


def test_non_image_upload_is_rejected(alice):
    album = alice.post(MEMORIES + "/albums", json={"title": "Test Album"}).json()
    files = {"file": ("evil.txt", b"not an image", "text/plain")}
    response = alice.post(f"{MEMORIES}/albums/{album['id']}/photos", files=files)
    assert response.status_code == 400


def test_deleting_album_removes_its_photos(alice):
    album = alice.post(MEMORIES + "/albums", json={"title": "Doomed Album"}).json()
    files = {"file": ("photo.jpg", make_jpeg_bytes(), "image/jpeg")}
    alice.post(f"{MEMORIES}/albums/{album['id']}/photos", files=files)

    response = alice.delete(f"{MEMORIES}/albums/{album['id']}")
    assert response.status_code == 200
    assert alice.get(f"{MEMORIES}/albums/{album['id']}").status_code == 404


# --- Cross-user isolation -------------------------------------------------


def test_cross_user_life_isolation(alice, bob):
    goal = alice.post(GOALS, json={"title": "Alice Goal"}).json()
    checklist = alice.post(CHECKLISTS, json={"title": "Alice Checklist"}).json()
    album = alice.post(MEMORIES + "/albums", json={"title": "Alice Album"}).json()

    assert bob.get(f"{GOALS}/{goal['id']}").status_code == 404
    assert bob.get(f"{CHECKLISTS}/{checklist['id']}").status_code == 404
    assert bob.get(f"{MEMORIES}/albums/{album['id']}").status_code == 404
    assert bob.get(GOALS).json() == []
    assert bob.get(CHECKLISTS).json() == []
    assert bob.get(MEMORIES + "/albums").json() == []
