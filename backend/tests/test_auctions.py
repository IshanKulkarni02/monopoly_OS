def _setup_game(client, num_players=2, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", **overrides}).json()
    code = data["game"]["code"]
    players = [{"id": data["host_player_id"], "token": data["player_token"], "name": "Alice"}]
    for name in ["Bob", "Carol", "Dave"][: num_players - 1]:
        r = client.post(f"/api/games/{code}/join", json={"name": name}).json()
        players.append({"id": r["player_id"], "token": r["player_token"], "name": name})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, players, data["host_token"]


def _headers(p):
    return {"x-player-id": p["id"], "x-player-token": p["token"]}


def _unowned_property(client, code):
    state = client.get(f"/api/games/{code}").json()
    return next(p for p in state["properties"] if p["owner_id"] is None and p["price"] > 0)


def test_auction_requires_auction_enabled(client):
    code, players, _host_token = _setup_game(client)
    prop = _unowned_property(client, code)
    r = client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(players[0]))
    assert r.status_code == 400


def test_auction_full_flow_highest_bidder_wins(client):
    code, players, _host_token = _setup_game(client, num_players=3, auction_enabled=True)
    prop = _unowned_property(client, code)
    alice, bob, carol = players

    r = client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(alice))
    assert r.status_code == 200
    assert r.json()["active_auction"]["property_id"] == prop["id"]

    r = client.post(f"/api/games/{code}/auctions/bid", json={"amount": 10}, headers=_headers(bob))
    assert r.status_code == 200
    assert r.json()["active_auction"]["current_bid"] == 10
    assert r.json()["active_auction"]["current_bidder_id"] == bob["id"]

    r = client.post(f"/api/games/{code}/auctions/bid", json={"amount": 50}, headers=_headers(carol))
    assert r.status_code == 200

    r = client.post(f"/api/games/{code}/auctions/pass", headers=_headers(bob))
    assert r.status_code == 200
    assert r.json()["active_auction"] != {}  # Alice (the starter) hasn't acted yet

    r = client.post(f"/api/games/{code}/auctions/pass", headers=_headers(alice))
    assert r.status_code == 200
    state = r.json()
    assert state["active_auction"] == {}  # resolved: only Carol left, she wins
    prop_after = next(p for p in state["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] == carol["id"]
    carol_after = next(p for p in state["players"] if p["id"] == carol["id"])
    assert carol_after["balance"] == 1500 - 50


def test_auction_fails_with_no_sale_if_everyone_passes(client):
    code, players, _host_token = _setup_game(client, num_players=2, auction_enabled=True)
    prop = _unowned_property(client, code)
    alice, bob = players

    client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(alice))
    client.post(f"/api/games/{code}/auctions/pass", headers=_headers(bob))
    r = client.post(f"/api/games/{code}/auctions/pass", headers=_headers(alice))
    assert r.status_code == 200
    state = r.json()
    assert state["active_auction"] == {}
    prop_after = next(p for p in state["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] is None


def test_cannot_bid_below_minimum_increment(client):
    code, players, _host_token = _setup_game(client, num_players=2, auction_enabled=True)
    prop = _unowned_property(client, code)
    alice, bob = players
    client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(alice))

    r = client.post(f"/api/games/{code}/auctions/bid", json={"amount": 5}, headers=_headers(bob))  # default min increment is 10
    assert r.status_code == 400


def test_current_bidder_cannot_pass(client):
    code, players, _host_token = _setup_game(client, num_players=2, auction_enabled=True)
    prop = _unowned_property(client, code)
    alice, bob = players
    client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(alice))
    client.post(f"/api/games/{code}/auctions/bid", json={"amount": 10}, headers=_headers(bob))

    r = client.post(f"/api/games/{code}/auctions/pass", headers=_headers(bob))
    assert r.status_code == 400


def test_only_one_auction_at_a_time(client):
    code, players, _host_token = _setup_game(client, num_players=2, auction_enabled=True)
    state = client.get(f"/api/games/{code}").json()
    unowned = [p for p in state["properties"] if p["owner_id"] is None and p["price"] > 0]
    alice = players[0]
    client.post(f"/api/games/{code}/auctions/start", json={"property_id": unowned[0]["id"]}, headers=_headers(alice))
    r = client.post(f"/api/games/{code}/auctions/start", json={"property_id": unowned[1]["id"]}, headers=_headers(alice))
    assert r.status_code == 400


def test_only_host_can_cancel_an_auction(client):
    code, players, host_token = _setup_game(client, num_players=2, auction_enabled=True)
    prop = _unowned_property(client, code)
    alice = players[0]
    client.post(f"/api/games/{code}/auctions/start", json={"property_id": prop["id"]}, headers=_headers(alice))

    r = client.post(f"/api/games/{code}/auctions/cancel", headers={"x-host-token": "wrong-token"})
    assert r.status_code == 403

    r = client.post(f"/api/games/{code}/auctions/cancel", headers={"x-host-token": host_token})
    assert r.status_code == 200
    assert r.json()["active_auction"] == {}
    prop_after = next(p for p in r.json()["properties"] if p["id"] == prop["id"])
    assert prop_after["owner_id"] is None
