from types import SimpleNamespace

from app.game_engine.bot_ai import _decide_jail_choice


def test_add_bot_requires_virtual_mode(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()  # default irl_companion
    r = client.post(f"/api/games/{data['game']['code']}/bots", json={}, headers={"x-host-token": data["host_token"]})
    assert r.status_code == 400


def test_add_bot_requires_host(client):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    r = client.post(f"/api/games/{data['game']['code']}/bots", json={})
    assert r.status_code == 403


def test_add_bot_success_and_sequential_naming(client):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]

    r = client.post(f"/api/games/{code}/bots", json={}, headers={"x-host-token": host_token})
    assert r.status_code == 200
    state = r.json()
    bots = [p for p in state["players"] if p["is_bot"]]
    assert len(bots) == 1
    assert bots[0]["name"] == "Bot 1"
    assert bots[0]["balance"] == 1500

    r = client.post(f"/api/games/{code}/bots", json={"name": "Rex"}, headers={"x-host-token": host_token})
    state = r.json()
    bots = sorted([p for p in state["players"] if p["is_bot"]], key=lambda p: p["name"])
    assert [b["name"] for b in bots] == ["Bot 1", "Rex"]


def test_cannot_add_bot_after_game_started(client):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    client.post(f"/api/games/{code}/bots", json={}, headers={"x-host-token": host_token})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    r = client.post(f"/api/games/{code}/bots", json={}, headers={"x-host-token": host_token})
    assert r.status_code == 400


def test_solo_play_bot_auto_plays_after_human_ends_turn(client, monkeypatch):
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: 3)  # dice always [3, 3], total 6

    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    client.post(f"/api/games/{code}/bots", json={}, headers={"x-host-token": data["host_token"]})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    state = client.get(f"/api/games/{code}").json()
    assert state["turn_order"][0] == host_id  # host (joined first) always goes first
    assert state["current_turn_player_id"] == host_id
    bot_id = next(p["id"] for p in state["players"] if p["is_bot"])

    client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": host_id, "x-player-token": host_token})

    r = client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": host_id, "x-player-token": host_token})
    assert r.status_code == 200
    final_state = r.json()

    # the bot should have auto-played its whole turn and handed control back to the host
    assert final_state["current_turn_player_id"] == host_id
    bot_state = next(p for p in final_state["players"] if p["id"] == bot_id)
    assert bot_state["position"] == 6  # moved by the same [3,3] roll

    oriental_ave = next(p for p in final_state["properties"] if p["name"] == "Oriental Avenue")
    assert oriental_ave["owner_id"] == bot_id
    assert bot_state["balance"] == 1500 - 100


def test_bot_jail_choice_uses_card_if_available():
    player = SimpleNamespace(jail_free_cards=1, balance=1000)
    assert _decide_jail_choice(player) == {"use_jail_free_card": True, "pay_fine": False}


def test_bot_jail_choice_pays_fine_if_affordable():
    player = SimpleNamespace(jail_free_cards=0, balance=1000)
    assert _decide_jail_choice(player) == {"pay_fine": True, "use_jail_free_card": False}


def test_bot_jail_choice_tries_roll_if_too_poor_to_pay():
    player = SimpleNamespace(jail_free_cards=0, balance=120)  # below CASH_BUFFER after the fine
    assert _decide_jail_choice(player) == {"use_jail_free_card": False, "pay_fine": False}
