from app.game_engine import currency as currency_engine


def test_make_change_endpoint_matches_spec_example(client):
    r = client.post("/api/currency/make_change", json={"amount": 70, "denominations": [10, 20, 50, 100, 200, 500]})
    assert r.status_code == 200
    assert r.json()["breakdown"] == {"50": 1, "20": 1}


def test_make_change_endpoint_rejects_unrepresentable_amount(client):
    r = client.post("/api/currency/make_change", json={"amount": 15, "denominations": [10, 20, 50]})
    assert r.status_code == 400


def _setup_tracked_game(client, **overrides):
    data = client.post(
        "/api/games",
        json={"host_name": "Alice", "board_key": "current_game", "banker_mode": "auto", **overrides},
    ).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_token, bob["player_id"], bob["player_token"]


def test_denominations_not_tracked_by_default(client):
    code, host_id, *_ = _setup_tracked_game(client)
    state = client.get(f"/api/games/{code}").json()
    host_state = next(p for p in state["players"] if p["id"] == host_id)
    assert host_state["denominations"] == {}


def test_denominations_seeded_at_creation_when_tracking_enabled(client):
    code, host_id, *_ = _setup_tracked_game(client, track_denominations=True)
    state = client.get(f"/api/games/{code}").json()
    assert state["ruleset"]["currency"]["track_denominations"] is True
    host_state = next(p for p in state["players"] if p["id"] == host_id)
    assert host_state["denominations"] != {}
    assert currency_engine.total_of(host_state["denominations"]) == host_state["balance"] == 5000


def test_denominations_seeded_for_players_who_join_after_creation(client):
    code, host_id, host_token, bob_id, _ = _setup_tracked_game(client, track_denominations=True)
    state = client.get(f"/api/games/{code}").json()
    bob_state = next(p for p in state["players"] if p["id"] == bob_id)
    assert currency_engine.total_of(bob_state["denominations"]) == bob_state["balance"]


def test_denominations_stay_in_sync_with_balance_through_a_purchase(client):
    code, host_id, host_token, bob_id, bob_token = _setup_tracked_game(client, track_denominations=True)
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["price"] > 0)

    r = client.post(f"/api/games/{code}/properties/{prop['id']}/purchase", headers={"x-player-id": host_id, "x-player-token": host_token})
    assert r.status_code == 200

    state_after = r.json()["game"]
    host_after = next(p for p in state_after["players"] if p["id"] == host_id)
    assert currency_engine.total_of(host_after["denominations"]) == host_after["balance"]
    assert host_after["balance"] == 5000 - prop["price"]


def test_mortgage_payoff_rounds_to_a_payable_note_when_tracking_enabled(client):
    # Regression: found via manual E2E, not a unit test — a mortgage payoff
    # (value * 1.1 interest) routinely isn't a multiple of the smallest
    # note (e.g. 170 * 1.1 = 187), which used to blow up as an uncaught
    # CurrencyError -> 500 instead of either succeeding or a clean 400.
    code, host_id, host_token, bob_id, bob_token = _setup_tracked_game(client, track_denominations=True)
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["price"] % 20 == 0 and p["price"] > 0)
    client.post(f"/api/games/{code}/properties/{prop['id']}/purchase", headers={"x-player-id": host_id, "x-player-token": host_token})
    client.post(f"/api/games/{code}/properties/{prop['id']}/mortgage", headers={"x-player-id": host_id, "x-player-token": host_token})

    r = client.post(f"/api/games/{code}/properties/{prop['id']}/unmortgage", headers={"x-player-id": host_id, "x-player-token": host_token})
    assert r.status_code == 200, r.text  # must not 500, and must not silently fail either

    host_after = next(p for p in r.json()["players"] if p["id"] == host_id)
    assert currency_engine.total_of(host_after["denominations"]) == host_after["balance"]
    assert host_after["balance"] % 10 == 0  # rounded to a payable note, not a fractional-note amount


def test_denominations_stay_in_sync_through_rent_payment(client):
    code, host_id, host_token, bob_id, bob_token = _setup_tracked_game(client, track_denominations=True)
    state = client.get(f"/api/games/{code}").json()
    board = client.get("/api/boards/current_game").json()
    crown_tiles = sorted([t for t in board["tiles"] if t["group_id"] == next(g["id"] for g in board["groups"] if g["key"] == "A")], key=lambda t: t["position"])
    crown_props = [next(p for p in state["properties"] if p["space_index"] == t["position"]) for t in crown_tiles]
    for prop in crown_props:
        client.post(f"/api/games/{code}/properties/{prop['id']}/purchase", headers={"x-player-id": host_id, "x-player-token": host_token})

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": crown_tiles[0]["position"]},
        headers={"x-player-token": bob_token},
    )
    assert r.status_code == 200
    assert r.json()["outcome"]["outcome"] == "rent_paid"

    state_after = r.json()["game"]
    bob_after = next(p for p in state_after["players"] if p["id"] == bob_id)
    host_after = next(p for p in state_after["players"] if p["id"] == host_id)
    assert currency_engine.total_of(bob_after["denominations"]) == bob_after["balance"]
    assert currency_engine.total_of(host_after["denominations"]) == host_after["balance"]
