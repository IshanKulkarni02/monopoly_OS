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


def test_trading_disabled_rejects_proposal(client):
    code, players = _setup_game(client, trading_enabled=False)
    alice, bob = players
    r = client.post(
        f"/api/games/{code}/trades",
        json={"recipient_id": bob["id"], "offer_cash": 10},
        headers=_headers(alice),
    )
    assert r.status_code == 400


def test_propose_and_accept_trade_swaps_everything(client):
    code, players = _setup_game(client)
    alice, bob = players
    state = client.get(f"/api/games/{code}").json()
    unowned = [p for p in state["properties"] if p["price"] > 0]
    prop_a, prop_b = unowned[0], unowned[1]
    _buy(client, code, alice, prop_a["id"])
    _buy(client, code, bob, prop_b["id"])

    before = client.get(f"/api/games/{code}").json()
    alice_before = next(p for p in before["players"] if p["id"] == alice["id"])
    bob_before = next(p for p in before["players"] if p["id"] == bob["id"])

    r = client.post(
        f"/api/games/{code}/trades",
        json={
            "recipient_id": bob["id"],
            "offer_cash": 50,
            "offer_property_ids": [prop_a["id"]],
            "request_property_ids": [prop_b["id"]],
        },
        headers=_headers(alice),
    )
    assert r.status_code == 200, r.text
    trade = r.json()
    assert trade["status"] == "pending"

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/accept", headers=_headers(bob))
    assert r.status_code == 200, r.text
    state = r.json()

    prop_a_after = next(p for p in state["properties"] if p["id"] == prop_a["id"])
    prop_b_after = next(p for p in state["properties"] if p["id"] == prop_b["id"])
    assert prop_a_after["owner_id"] == bob["id"]
    assert prop_b_after["owner_id"] == alice["id"]

    alice_after = next(p for p in state["players"] if p["id"] == alice["id"])
    bob_after = next(p for p in state["players"] if p["id"] == bob["id"])
    assert alice_after["balance"] == alice_before["balance"] - 50
    assert bob_after["balance"] == bob_before["balance"] + 50
    assert state["pending_trades"] == []


def test_only_recipient_can_accept_or_decline(client):
    code, players = _setup_game(client)
    alice, bob = players
    trade = client.post(
        f"/api/games/{code}/trades", json={"recipient_id": bob["id"], "offer_cash": 10}, headers=_headers(alice)
    ).json()

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/accept", headers=_headers(alice))
    assert r.status_code == 403


def test_decline_trade_leaves_state_unchanged(client):
    code, players = _setup_game(client)
    alice, bob = players
    trade = client.post(
        f"/api/games/{code}/trades", json={"recipient_id": bob["id"], "offer_cash": 10}, headers=_headers(alice)
    ).json()

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/decline", headers=_headers(bob))
    assert r.status_code == 200
    alice_after = next(p for p in r.json()["players"] if p["id"] == alice["id"])
    assert alice_after["balance"] == 1500  # nothing moved


def test_proposer_can_cancel_a_pending_trade(client):
    code, players = _setup_game(client)
    alice, bob = players
    trade = client.post(
        f"/api/games/{code}/trades", json={"recipient_id": bob["id"], "offer_cash": 10}, headers=_headers(alice)
    ).json()

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/cancel", headers=_headers(bob))
    assert r.status_code == 403  # only the proposer (or host) can cancel

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/cancel", headers=_headers(alice))
    assert r.status_code == 200
    assert r.json()["pending_trades"] == []


def test_cannot_offer_a_property_you_do_not_own(client):
    code, players = _setup_game(client)
    alice, bob = players
    state = client.get(f"/api/games/{code}").json()
    someone_elses = next(p for p in state["properties"] if p["price"] > 0)

    r = client.post(
        f"/api/games/{code}/trades",
        json={"recipient_id": bob["id"], "offer_property_ids": [someone_elses["id"]]},
        headers=_headers(alice),
    )
    assert r.status_code == 400


def test_accept_revalidates_if_proposer_spent_the_offered_cash_meanwhile(client):
    code, players = _setup_game(client)
    alice, bob = players
    trade = client.post(
        f"/api/games/{code}/trades", json={"recipient_id": bob["id"], "offer_cash": 1000}, headers=_headers(alice)
    ).json()

    # Alice spends most of her cash on something else before Bob responds.
    client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": alice["id"], "to_player_id": None, "amount": 1000, "reason": "unrelated spend"},
        headers=_headers(alice),
    )

    r = client.post(f"/api/games/{code}/trades/{trade['id']}/accept", headers=_headers(bob))
    assert r.status_code == 400
    # Rejected, not silently auto-declined — the trade is still pending and
    # can be explicitly cancelled/declined once Bob sees why it failed.
    trades = client.get(f"/api/games/{code}/trades").json()
    assert next(t for t in trades if t["id"] == trade["id"])["status"] == "pending"
