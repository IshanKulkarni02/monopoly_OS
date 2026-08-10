def _setup_auto_game(client, **overrides):
    data = client.post(
        "/api/games", json={"host_name": "Alice", "banker_mode": "auto", **overrides}
    ).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_player_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_player_token, bob["player_id"], bob["player_token"]


def test_on_pass_go_inflation_scales_rent(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(
        client, inflation_enabled=True, inflation_trigger="on_pass_go", inflation_rate=0.5
    )
    state = client.get(f"/api/games/{code}").json()
    med_ave = next(p for p in state["properties"] if p["name"] == "Mediterranean Avenue")
    client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )

    # Bob passes GO once -> multiplier becomes 1.5
    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 0},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["game"]["inflation_multiplier"] == 1.5

    # Bob lands on Mediterranean Ave -> base rent $2, scaled to $3 (round(2 * 1.5))
    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 1},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "rent_paid"
    assert r.json()["outcome"]["amount"] == 3


def test_tax_scope_respected(client):
    # scope defaults to ["rent", "tax"] — verify tax is scaled too
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(
        client, inflation_enabled=True, inflation_trigger="on_pass_go", inflation_rate=1.0
    )
    client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 0},
        headers={"x-player-token": bob_token},
    )  # multiplier -> 2.0

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 4},  # Income Tax, base $200
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "tax_paid"
    assert r.json()["outcome"]["amount"] == 400


def test_per_round_trigger_only_advances_on_round_advance(client):
    code, host_id, host_token, bob_id, bob_token = _setup_auto_game(
        client, inflation_enabled=True, inflation_trigger="per_round", inflation_rate=0.25
    )
    # passing GO shouldn't move the multiplier under a per_round trigger
    client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 0},
        headers={"x-player-token": bob_token},
    )
    state = client.get(f"/api/games/{code}").json()
    assert state["inflation_multiplier"] == 1.0
    assert state["round_number"] == 1

    r = client.post(
        f"/api/games/{code}/advance_round",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200
    assert r.json()["round_number"] == 2
    assert r.json()["inflation_multiplier"] == 1.25

    # non-banker can't advance the round
    r = client.post(
        f"/api/games/{code}/advance_round",
        headers={"x-player-id": bob_id, "x-player-token": bob_token},
    )
    assert r.status_code == 403
