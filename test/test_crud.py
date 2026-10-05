"""
Тести CRUD-логіки доступу до БД (через реальні API-ендпоінти, які всередині
викликають ORM-шар app/crud, app/services). 6 сценаріїв: реєстрація/читання,
конфлікт унікальності, логін (успіх/невдача), права доступу на деактивацію,
валідація складу команди, повний цикл матчу + захист цілісності при видаленні.

Запуск:
    pytest -v
Вимагає запущеної та ініціалізованої (sql/dump.sql або schema.sql+seed_ranks.sql) БД,
на яку вказує DATABASE_URL з .env - так само, як і сам застосунок.
"""

import uuid


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register(client, username=None, password="password123"):
    username = username or _unique_username("u")
    resp = client.post("/users/", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
    })
    assert resp.status_code == 201, resp.text
    return resp.json(), password


# ------------------------------------------------------------
# 1. USERS: CREATE + READ (позитивний сценарій)
# ------------------------------------------------------------
def test_register_and_read_user(client):
    user, _ = _register(client)

    assert user["role"] == "user"
    assert user["is_active"] is True

    resp = client.get(f"/users/{user['id']}")
    assert resp.status_code == 200
    assert resp.json()["username"] == user["username"]

    # Стартовий рейтинг 1000 MMR створюється автоматично для обох режимів
    for mode in ("solo", "party"):
        rating = client.get(f"/users/{user['id']}/rating/{mode}")
        assert rating.status_code == 200, rating.text
        assert rating.json()["mmr"] == 1000


# ------------------------------------------------------------
# 2. USERS: UNIQUE-обмеження (негативний сценарій)
# ------------------------------------------------------------
def test_register_duplicate_username_conflicts(client):
    username = _unique_username("dup")
    first, _ = _register(client, username=username)
    assert first["username"] == username

    resp = client.post("/users/", json={
        "username": username,
        "email": f"other_{username}@example.com",
        "password": "password123",
    })
    assert resp.status_code == 409


# ------------------------------------------------------------
# 3. LOGIN: успіх і невдача
# ------------------------------------------------------------
def test_login_success_and_wrong_password(client):
    user, password = _register(client)

    ok = client.post("/users/login", json={"username": user["username"], "password": password})
    assert ok.status_code == 200
    assert ok.json()["id"] == user["id"]

    bad = client.post("/users/login", json={"username": user["username"], "password": "totally-wrong"})
    assert bad.status_code == 401


# ------------------------------------------------------------
# 4. UPDATE / DELETE: розмежування прав (лише власник або admin)
# ------------------------------------------------------------
def test_deactivate_requires_self_or_admin(client):
    owner, _ = _register(client)
    stranger, _ = _register(client)

    # Чужий звичайний користувач НЕ може деактивувати акаунт іншого
    forbidden = client.delete(f"/users/{owner['id']}", params={"requester_id": stranger["id"]})
    assert forbidden.status_code == 403

    # Сам власник - може
    ok = client.delete(f"/users/{owner['id']}", params={"requester_id": owner["id"]})
    assert ok.status_code == 200
    assert ok.json()["is_active"] is False

    # Деактивований акаунт більше не логіниться
    login_after = client.post("/users/login", json={"username": owner["username"], "password": "password123"})
    assert login_after.status_code == 403


# ------------------------------------------------------------
# 5. TEAMS: валідація складу команди (3 різних гравці)
# ------------------------------------------------------------
def test_create_team_validates_member_count(client):
    u1, _ = _register(client)
    u2, _ = _register(client)
    u3, _ = _register(client)

    ok = client.post("/teams/", json={
        "name": "Test Team",
        "member_user_ids": [u1["id"], u2["id"], u3["id"]],
        "is_permanent": False,
    })
    assert ok.status_code == 201, ok.text
    assert len(ok.json()["member_user_ids"]) == 3

    # Дубльований гравець -> лишається лише 2 унікальних ID -> 400
    bad = client.post("/teams/", json={
        "member_user_ids": [u1["id"], u1["id"], u2["id"]],
        "is_permanent": False,
    })
    assert bad.status_code == 400


# ------------------------------------------------------------
# 6. MATCHES: повний цикл (створення -> скасування/видалення,
#    та захист цілісності - завершений матч видалити не можна)
# ------------------------------------------------------------
def test_solo_match_cancel_and_delete_protection(client):
    p1, _ = _register(client)
    p2, _ = _register(client)

    # Матч без зіграних раундів можна скасувати і видалити
    m1 = client.post("/matches/solo", json={"player1_id": p1["id"], "player2_id": p2["id"]})
    assert m1.status_code == 201
    match1_id = m1.json()["id"]

    cancel = client.post(f"/matches/{match1_id}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    delete = client.delete(f"/matches/{match1_id}")
    assert delete.status_code == 204

    # Другий матч доводимо до фіналу (2 перемоги) - тоді видалення заборонене
    m2 = client.post("/matches/solo", json={"player1_id": p1["id"], "player2_id": p2["id"]})
    assert m2.status_code == 201
    match2_id = m2.json()["id"]

    status = "in_progress"
    for _ in range(20):  # coin_result випадковий на сервері - граємо, поки не завершиться
        round_resp = client.post(f"/matches/{match2_id}/rounds", json={"coin_choice": "heads"})
        assert round_resp.status_code == 201, round_resp.text
        match_state = client.get(f"/matches/{match2_id}")
        status = match_state.json()["status"]
        if status == "finished":
            break
    assert status == "finished"

    # Не можна скасувати вже завершений матч
    cancel_finished = client.post(f"/matches/{match2_id}/cancel")
    assert cancel_finished.status_code == 400

    # Не можна видалити завершений матч (захист цілісності rating_history)
    delete_finished = client.delete(f"/matches/{match2_id}")
    assert delete_finished.status_code == 409

    # MMR обох гравців справді змінився (Elo-перерахунок відбувся)
    r1 = client.get(f"/users/{p1['id']}/rating/solo").json()
    r2 = client.get(f"/users/{p2['id']}/rating/solo").json()
    assert r1["mmr"] != 1000 or r2["mmr"] != 1000
    assert r1["matches_played"] == 1
    assert r2["matches_played"] == 1
