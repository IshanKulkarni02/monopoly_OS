from app.game_engine.events.base import EventOutcome


def _setup_game(client, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", **overrides}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_player_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_player_token, bob["player_id"], bob["player_token"]


def test_draw_event_rejects_non_event_space(client):
    code, host_id, host_token, *_ = _setup_game(client)
    r = client.post(
        f"/api/games/{code}/draw_event",
        json={"player_id": host_id, "space_index": 1},  # Mediterranean Ave, not an event space
        headers={"x-player-token": host_token},
    )
    assert r.status_code == 400


def test_cards_bank_pays_outcome(client, monkeypatch):
    code, host_id, host_token, *_ = _setup_game(client)  # default event_system=cards
    monkeypatch.setattr(
        "app.game_engine.events.cards.draw",
        lambda deck: EventOutcome("bank_pays", 150, "Test payout"),
    )
    r = client.post(
        f"/api/games/{code}/draw_event",
        json={"player_id": host_id, "space_index": 7},  # Chance
        headers={"x-player-token": host_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"]["kind"] == "bank_pays"
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1650


def test_wheel_pay_each_player_outcome(client, monkeypatch):
    code, host_id, host_token, bob_id, _ = _setup_game(client, event_system="wheel")
    monkeypatch.setattr(
        "app.game_engine.events.wheel.spin",
        lambda: EventOutcome("pay_each_player", 25, "Test party"),
    )
    r = client.post(
        f"/api/games/{code}/draw_event",
        json={"player_id": host_id, "space_index": 7},  # any chance/community space triggers the wheel
        headers={"x-player-token": host_token},
    )
    assert r.status_code == 200
    body = r.json()
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    bob_state = next(p for p in body["game"]["players"] if p["id"] == bob_id)
    assert host_state["balance"] == 1475
    assert bob_state["balance"] == 1525


def test_jail_free_card_increments_counter(client, monkeypatch):
    code, host_id, host_token, *_ = _setup_game(client)
    monkeypatch.setattr(
        "app.game_engine.events.cards.draw",
        lambda deck: EventOutcome("jail_free", 0, "Test voucher"),
    )
    r = client.post(
        f"/api/games/{code}/draw_event",
        json={"player_id": host_id, "space_index": 17},  # Community Chest
        headers={"x-player-token": host_token},
    )
    assert r.status_code == 200
    host_state = next(p for p in r.json()["game"]["players"] if p["id"] == host_id)
    assert host_state["jail_free_cards"] == 1


def test_pass_go_outcome_awards_bonus(client, monkeypatch):
    code, host_id, host_token, *_ = _setup_game(client)
    monkeypatch.setattr(
        "app.game_engine.events.cards.draw",
        lambda deck: EventOutcome("pass_go", 0, "Test shortcut"),
    )
    r = client.post(
        f"/api/games/{code}/draw_event",
        json={"player_id": host_id, "space_index": 7},
        headers={"x-player-token": host_token},
    )
    host_state = next(p for p in r.json()["game"]["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1700


def test_challenge_before_buy_failure_blocks_purchase(client, monkeypatch):
    code, host_id, host_token, *_ = _setup_game(client, challenge_before_buy=True)
    monkeypatch.setattr("app.game_engine.challenges.run_challenge", lambda game: (False, 12))

    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["name"] == "Boardwalk")

    r = client.post(
        f"/api/games/{code}/properties/{prop['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["purchased"] is False
    assert body["challenge"]["passed"] is False
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1500  # untouched
    prop_after = next(p for p in body["game"]["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] is None


def test_challenge_before_buy_success_completes_purchase(client, monkeypatch):
    code, host_id, host_token, *_ = _setup_game(client, challenge_before_buy=True)
    monkeypatch.setattr("app.game_engine.challenges.run_challenge", lambda game: (True, 88))

    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["name"] == "Boardwalk")

    r = client.post(
        f"/api/games/{code}/properties/{prop['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    body = r.json()
    assert body["purchased"] is True
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["balance"] == 1500 - 400
