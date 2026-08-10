def _setup_virtual_game(client, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual", **overrides}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_player_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_player_token, bob["player_id"], bob["player_token"]


def test_turn_order_seeded_on_start(client):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)
    state = client.get(f"/api/games/{code}").json()
    assert state["turn_order"] == [host_id, bob_id]
    assert state["current_turn_player_id"] == host_id


def test_only_current_player_can_roll(client):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)

    r = client.post(
        f"/api/games/{code}/roll",
        json={},
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 400

    r = client.post(
        f"/api/games/{code}/roll",
        json={},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200


def test_roll_moves_player_and_resolves_landing(client, monkeypatch):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: 3)  # dice = [3, 3], total 6

    r = client.post(
        f"/api/games/{code}/roll",
        json={},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["outcome"] == "moved"
    assert body["result"]["position"] == 6  # 0 + 6, space 6 = Oriental Avenue, unowned
    assert body["result"]["landing"]["outcome"] == "purchasable"
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["position"] == 6


def test_passing_go_awards_bonus_without_double_counting(client, monkeypatch):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: 6)  # dice = [6, 6], total 12

    def roll(player_id, token):
        return client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": player_id, "x-player-token": token})

    def end_turn(player_id, token):
        client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": player_id, "x-player-token": token})

    # host: 0 -> 12 -> 24 -> 36 (three +12 rolls, no wrap yet)
    for _ in range(3):
        roll(host_id, host_token)
        end_turn(host_id, host_token)
        roll(bob_id, bob_token)
        end_turn(bob_id, bob_token)

    state = client.get(f"/api/games/{code}").json()
    host_before = next(p for p in state["players"] if p["id"] == host_id)
    assert host_before["position"] == 36
    balance_before = host_before["balance"]

    r = roll(host_id, host_token)  # 36 + 12 = 48 % 40 = 8 -> wraps past GO
    body = r.json()
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["position"] == 8
    # exactly one $200 pass-go bonus applied for this wrap
    assert host_state["balance"] == balance_before + 200


def test_end_turn_advances_and_requires_current_player(client):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)

    r = client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": bob_id, "x-player-token": bob_token})
    assert r.status_code == 400

    r = client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": host_id, "x-player-token": host_token})
    assert r.status_code == 200
    assert r.json()["current_turn_player_id"] == bob_id


def test_go_to_jail_space_sends_player_to_jail(client, monkeypatch):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: 5)  # dice=[5,5], total 10

    # host: 0 -> 10 (Jail, just visiting)
    client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": host_id, "x-player-token": host_token})
    client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": host_id, "x-player-token": host_token})
    client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": bob_id, "x-player-token": bob_token})
    client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": bob_id, "x-player-token": bob_token})
    # host: 10 -> 20 (Free Parking)
    client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": host_id, "x-player-token": host_token})
    client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": host_id, "x-player-token": host_token})
    client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": bob_id, "x-player-token": bob_token})
    client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": bob_id, "x-player-token": bob_token})
    # host: 20 -> 30 (Go To Jail)
    r = client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": host_id, "x-player-token": host_token})
    body = r.json()
    assert body["result"]["landing"]["outcome"] == "sent_to_jail"
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["in_jail"] is True
    assert host_state["position"] == 10


def test_jail_stay_then_release_via_doubles(client, monkeypatch):
    code, host_id, host_token, bob_id, bob_token = _setup_virtual_game(client)

    # Two dice values per roll; laid out roll-by-roll for readability.
    dice_queue = iter(
        [
            5, 5,  # host: 0 -> 10 (Jail, just visiting)
            5, 5,  # bob: 0 -> 10
            5, 5,  # host: 10 -> 20 (Free Parking)
            5, 5,  # bob: 10 -> 20
            5, 5,  # host: 20 -> 30 (Go To Jail!) -> in_jail, position reset to 10
            1, 1,  # bob: irrelevant roll
            1, 2,  # host (in jail): not doubles -> stays in jail, turn auto-ends
            1, 1,  # bob: irrelevant roll
            3, 3,  # host (in jail): doubles -> released, moves 10 -> 16
        ]
    )
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: next(dice_queue))

    def roll(player_id, token):
        return client.post(f"/api/games/{code}/roll", json={}, headers={"x-player-id": player_id, "x-player-token": token})

    def end_turn(player_id, token):
        client.post(f"/api/games/{code}/end_turn", headers={"x-player-id": player_id, "x-player-token": token})

    roll(host_id, host_token)
    end_turn(host_id, host_token)
    roll(bob_id, bob_token)
    end_turn(bob_id, bob_token)
    roll(host_id, host_token)
    end_turn(host_id, host_token)
    roll(bob_id, bob_token)
    end_turn(bob_id, bob_token)

    r = roll(host_id, host_token)  # lands on Go To Jail
    host_state = next(p for p in r.json()["game"]["players"] if p["id"] == host_id)
    assert host_state["in_jail"] is True
    end_turn(host_id, host_token)

    roll(bob_id, bob_token)
    end_turn(bob_id, bob_token)

    r = roll(host_id, host_token)  # jail roll #1: no doubles -> stays in jail
    body = r.json()
    assert body["result"]["outcome"] == "stayed_in_jail"
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["in_jail"] is True
    assert host_state["jail_turns"] == 1
    # a stayed-in-jail roll ends the turn on its own
    assert body["game"]["current_turn_player_id"] == bob_id

    roll(bob_id, bob_token)
    end_turn(bob_id, bob_token)

    r = roll(host_id, host_token)  # jail roll #2: doubles -> released and moves
    body = r.json()
    assert body["result"]["outcome"] == "moved"
    host_state = next(p for p in body["game"]["players"] if p["id"] == host_id)
    assert host_state["in_jail"] is False
    assert host_state["jail_turns"] == 0
    assert host_state["position"] == 16
