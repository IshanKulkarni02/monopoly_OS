def _setup_game(client, num_players=2, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", **overrides}).json()
    code = data["game"]["code"]
    players = [{"id": data["host_player_id"], "token": data["player_token"], "name": "Alice"}]
    for name in ["Bob", "Carol"][: num_players - 1]:
        r = client.post(f"/api/games/{code}/join", json={"name": name}).json()
        players.append({"id": r["player_id"], "token": r["player_token"], "name": name})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, players


def _headers(p):
    return {"x-player-id": p["id"], "x-player-token": p["token"]}


def _buy(client, code, player, prop_id):
    r = client.post(f"/api/games/{code}/properties/{prop_id}/purchase", headers=_headers(player))
    assert r.status_code == 200, r.text


def test_bankruptcy_to_the_bank_resets_properties_to_unowned(client):
    code, players = _setup_game(client)
    alice, bob = players
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["price"] > 0)
    _buy(client, code, alice, prop["id"])

    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 200, r.text
    state = r.json()

    alice_after = next(p for p in state["players"] if p["id"] == alice["id"])
    assert alice_after["status"] == "bankrupt"
    assert alice_after["balance"] == 0

    prop_after = next(p for p in state["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] is None
    assert prop_after["mortgaged"] is False  # fresh/available again, not a dead mortgaged tile


def test_bankruptcy_to_a_player_transfers_everything(client):
    code, players = _setup_game(client)
    alice, bob = players
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["price"] > 0)
    _buy(client, code, alice, prop["id"])

    alice_before = next(p for p in client.get(f"/api/games/{code}").json()["players"] if p["id"] == alice["id"])

    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={"creditor_player_id": bob["id"]}, headers=_headers(alice))
    assert r.status_code == 200, r.text
    state = r.json()

    bob_after = next(p for p in state["players"] if p["id"] == bob["id"])
    alice_after = next(p for p in state["players"] if p["id"] == alice["id"])
    assert alice_after["status"] == "bankrupt"
    assert alice_after["balance"] == 0
    # Bob gets Alice's remaining cash *plus* the mortgage-value cash raised
    # by liquidating her property on the way to going bankrupt.
    mortgage_value = round(prop["price"] * 0.5)
    assert bob_after["balance"] == 1500 + alice_before["balance"] + mortgage_value

    prop_after = next(p for p in state["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] == bob["id"]
    assert prop_after["mortgaged"] is True  # Bob inherits it mortgaged; he can unmortgage later


def test_bankruptcy_liquidates_houses_and_mortgages_before_paying_out(client):
    code, players = _setup_game(client)
    alice, bob = players
    state = client.get(f"/api/games/{code}").json()
    board = client.get("/api/boards/classic").json()
    # Find a full color group Alice can buy outright to build on.
    group_id = next(g["id"] for g in board["groups"] if len([t for t in board["tiles"] if t["group_id"] == g["id"]]) == 2)
    tiles = sorted([t for t in board["tiles"] if t["group_id"] == group_id], key=lambda t: t["position"])
    props = [next(p for p in state["properties"] if p["space_index"] == t["position"]) for t in tiles]
    for p in props:
        _buy(client, code, alice, p["id"])

    r = client.post(f"/api/games/{code}/properties/{props[0]['id']}/build_house", headers=_headers(alice))
    assert r.status_code == 200, r.text
    r = client.post(f"/api/games/{code}/properties/{props[1]['id']}/build_house", headers=_headers(alice))
    assert r.status_code == 200, r.text

    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 200, r.text
    state = r.json()
    for p in props:
        prop_after = next(pp for pp in state["properties"] if pp["id"] == p["id"])
        assert prop_after["houses"] == 0
        assert prop_after["owner_id"] is None


def test_cannot_declare_bankruptcy_twice(client):
    code, players = _setup_game(client)
    alice, _bob = players
    client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 400


def test_bankrupt_player_is_skipped_in_turn_order(client):
    code, players = _setup_game(client, num_players=3, play_mode="virtual")
    alice, bob, carol = players
    state = client.get(f"/api/games/{code}").json()
    assert state["current_turn_player_id"] == alice["id"]

    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 200
    assert r.json()["current_turn_player_id"] == bob["id"]

    # End Bob's turn — should skip the now-bankrupt Alice and go to Carol.
    r = client.post(f"/api/games/{code}/end_turn", headers=_headers(bob))
    assert r.status_code == 200
    assert r.json()["current_turn_player_id"] == carol["id"]


def test_bot_goes_bankrupt_to_the_owner_instead_of_freezing_when_it_cannot_pay_rent(client, monkeypatch):
    # Deterministic dice (always [3, 3], total 6) — same technique
    # test_bots.py uses — so both Alice's and the bot's rolls land on
    # position 6 (Oriental Avenue) instead of depending on RNG luck.
    monkeypatch.setattr("app.game_engine.turn_engine.random.randint", lambda a, b: 3)

    data = client.post("/api/games", json={"host_name": "Alice", "play_mode": "virtual"}).json()
    code = data["game"]["code"]
    alice = {"id": data["host_player_id"], "token": data["player_token"]}
    client.post(f"/api/games/{code}/bots", json={"name": "Rusty"}, headers={"x-host-token": data["host_token"]})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    state = client.get(f"/api/games/{code}").json()
    bot = next(p for p in state["players"] if p["is_bot"])
    assert state["current_turn_player_id"] == alice["id"]

    r = client.post(f"/api/games/{code}/roll", json={}, headers=_headers(alice))
    assert r.status_code == 200
    oriental = next(p for p in r.json()["game"]["properties"] if p["name"] == "Oriental Avenue")
    _buy(client, code, alice, oriental["id"])

    board = client.get("/api/boards/classic").json()
    tile = next(t for t in board["tiles"] if t["name"] == "Oriental Avenue")
    rent = tile["rent_table"][0]

    # Drain the bot to just under the rent it's about to owe Alice.
    client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": bot["id"], "to_player_id": None, "amount": bot["balance"] - (rent - 1), "reason": "test drain"},
        headers=_headers(alice),
    )
    alice_before = next(p for p in client.get(f"/api/games/{code}").json()["players"] if p["id"] == alice["id"])

    r = client.post(f"/api/games/{code}/end_turn", headers=_headers(alice))
    assert r.status_code == 200
    final = r.json()

    bot_final = next(p for p in final["players"] if p["id"] == bot["id"])
    alice_final = next(p for p in final["players"] if p["id"] == alice["id"])
    assert bot_final["status"] == "bankrupt"
    assert bot_final["balance"] == 0
    assert alice_final["balance"] == alice_before["balance"] + (rent - 1)  # got the bot's entire remaining cash
    # The game kept moving — turn passed all the way back to Alice (the only
    # other active player) instead of freezing on the insolvent bot.
    assert final["current_turn_player_id"] == alice["id"]
