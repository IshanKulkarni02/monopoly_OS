def _setup_game(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_token, bob["player_id"], bob["player_token"]


def test_stats_before_any_activity(client):
    code, host_id, *_ = _setup_game(client)
    r = client.get(f"/api/games/{code}/stats")
    assert r.status_code == 200
    stats = r.json()
    assert len(stats["players"]) == 2
    assert all(p["net_worth"] == 1500 for p in stats["players"])
    assert stats["total_transactions"] == 0
    assert stats["most_valuable_property"] is None


def test_stats_reflects_purchases_and_ranks_by_net_worth(client):
    code, host_id, host_token, bob_id, bob_token = _setup_game(client)
    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["name"] == "Boardwalk")  # price 400
    client.post(f"/api/games/{code}/properties/{prop['id']}/purchase", headers={"x-player-id": host_id, "x-player-token": host_token})

    r = client.get(f"/api/games/{code}/stats")
    stats = r.json()
    assert stats["total_transactions"] == 1
    assert stats["total_money_moved"] == 400
    assert stats["most_valuable_property"] == {"name": "Boardwalk", "price": 400, "owner_name": "Alice"}
    alice_stats = next(p for p in stats["players"] if p["name"] == "Alice")
    assert alice_stats["properties_owned"] == 1
    assert alice_stats["net_worth"] == 1500  # cash spent, but property value offsets it


def test_stats_excludes_a_reversed_transaction_itself_but_counts_the_reversal(client):
    code, host_id, host_token, bob_id, bob_token = _setup_game(client)
    r = client.post(
        f"/api/games/{code}/transactions",
        json={"from_player_id": None, "to_player_id": bob_id, "amount": 100, "reason": "gift"},
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    txn_id = next(e["payload"]["transaction_id"] for e in r.json()["recent_log"] if e["kind"] == "transaction")
    client.post(f"/api/games/{code}/transactions/{txn_id}/reverse", headers={"x-player-id": host_id, "x-player-token": host_token})

    stats = client.get(f"/api/games/{code}/stats").json()
    # The original gift is marked reversed and excluded; the reversal itself
    # is a distinct, never-reversed transaction and counts — "money moved"
    # tracks real transfer activity, not net economic effect, so a
    # send-then-undo is two real movements, not zero.
    assert stats["total_money_moved"] == 100
    assert stats["total_transactions"] == 1
