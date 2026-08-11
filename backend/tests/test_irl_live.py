def _setup_irl_game(client, **overrides):
    data = client.post("/api/games", json={"host_name": "Host", "banker_mode": "auto", **overrides}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["host_token"]
    host_player_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})
    return code, host_id, host_token, host_player_token, bob["player_id"], bob["player_token"]


def test_irl_game_has_no_turn_order_until_ceremony_runs(client):
    code, *_ = _setup_irl_game(client)
    state = client.get(f"/api/games/{code}").json()
    assert state["turn_order"] == []
    assert state["current_turn_player_id"] is None


def test_ceremony_highest_roll_goes_first_by_default(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client)

    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": 4}, headers={"x-host-token": host_token})
    assert r.status_code == 200
    assert r.json()["outcome"]["outcome"] == "recorded"

    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": bob_id, "roll": 6}, headers={"x-host-token": host_token})
    assert r.status_code == 200
    assert r.json()["outcome"]["outcome"] == "order_set"
    state = r.json()["game"]
    assert state["turn_order"] == [bob_id, host_id]
    assert state["current_turn_player_id"] == bob_id
    assert state["pending_turn_order_rolls"] == []


def test_ceremony_entry_order_mode(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client, turn_order_mode="entry_order")

    client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": 1}, headers={"x-host-token": host_token})
    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": bob_id, "roll": 6}, headers={"x-host-token": host_token})
    state = r.json()["game"]
    # host entered first even though bob rolled higher -> host still goes first
    assert state["turn_order"] == [host_id, bob_id]


def test_ceremony_tie_requires_reroll(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client)

    client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": 5}, headers={"x-host-token": host_token})
    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": bob_id, "roll": 5}, headers={"x-host-token": host_token})
    assert r.json()["outcome"]["outcome"] == "tie"
    state = client.get(f"/api/games/{code}").json()
    assert state["turn_order"] == []
    assert state["pending_turn_order_rolls"] == []  # tied players' rolls cleared, ready to re-roll


def test_player_can_self_record_their_own_ceremony_roll(client):
    code, host_id, host_token, _hp_token, bob_id, bob_token = _setup_irl_game(client)
    r = client.post(
        f"/api/games/{code}/roll_for_order",
        json={"player_id": bob_id, "roll": 3},
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 200

    # a random other player can't record on bob's behalf without host or bob's own token
    r = client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": 2})
    assert r.status_code == 403


def _run_ceremony(client, code, host_token, host_id, bob_id, host_roll=6, bob_roll=2):
    client.post(f"/api/games/{code}/roll_for_order", json={"player_id": host_id, "roll": host_roll}, headers={"x-host-token": host_token})
    client.post(f"/api/games/{code}/roll_for_order", json={"player_id": bob_id, "roll": bob_roll}, headers={"x-host-token": host_token})


def test_roll_for_player_moves_and_resolves_landing(client, monkeypatch):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client)
    _run_ceremony(client, code, host_token, host_id, bob_id)  # host rolls higher -> host is current player

    r = client.post(
        f"/api/games/{code}/roll_for_player",
        json={"player_id": host_id, "dice": [3, 4]},
        headers={"x-host-token": host_token},
    )
    assert r.status_code == 200
    body = r.json()["result"]
    assert body["outcome"] == "moved"
    assert body["dice"] == [3, 4]
    assert body["position"] == 7  # 0 + 7 = Chance on the classic board
    assert body["landing"]["space_type"] == "mystery"
    assert "event" in body["landing"]  # auto-drawn since there's no physical deck once positions are tracked


def test_roll_for_player_rejects_wrong_dice_count(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client, dice_count=1)
    _run_ceremony(client, code, host_token, host_id, bob_id)

    r = client.post(
        f"/api/games/{code}/roll_for_player",
        json={"player_id": host_id, "dice": [3, 4]},
        headers={"x-host-token": host_token},
    )
    assert r.status_code == 400


def test_move_player_relocates_and_resolves_landing(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client)
    _run_ceremony(client, code, host_token, host_id, bob_id)

    r = client.post(
        f"/api/games/{code}/players/{bob_id}/move",
        json={"player_id": bob_id, "position": 5},
        headers={"x-host-token": host_token},
    )
    assert r.status_code == 200
    bob_state = next(p for p in r.json()["players"] if p["id"] == bob_id)
    assert bob_state["position"] == 5


def test_swap_players_exchanges_positions(client):
    code, host_id, host_token, _hp_token, bob_id, _bob_token = _setup_irl_game(client)
    _run_ceremony(client, code, host_token, host_id, bob_id)
    client.post(f"/api/games/{code}/players/{bob_id}/move", json={"player_id": bob_id, "position": 5}, headers={"x-host-token": host_token})
    client.post(f"/api/games/{code}/players/{host_id}/move", json={"player_id": host_id, "position": 9, "resolve_landing": False}, headers={"x-host-token": host_token})

    r = client.post(
        f"/api/games/{code}/players/swap",
        json={"player_a_id": bob_id, "player_b_id": host_id},
        headers={"x-host-token": host_token},
    )
    assert r.status_code == 200
    state = {p["id"]: p["position"] for p in r.json()["players"]}
    assert state[bob_id] == 9
    assert state[host_id] == 5


def test_player_tokens_is_host_only(client):
    code, host_id, host_token, _hp_token, bob_id, bob_token = _setup_irl_game(client)
    r = client.get(f"/api/games/{code}/player_tokens")
    assert r.status_code == 403

    r = client.get(f"/api/games/{code}/player_tokens", headers={"x-host-token": host_token})
    assert r.status_code == 200
    tokens = r.json()
    assert set(tokens.keys()) == {host_id, bob_id}
    assert tokens[bob_id] == bob_token
