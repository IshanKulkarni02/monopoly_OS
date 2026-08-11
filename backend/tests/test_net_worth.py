def _setup_owned_property(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    state = client.get(f"/api/games/{code}").json()
    prop = next(p for p in state["properties"] if p["name"] == "Boardwalk")  # price 400
    client.post(
        f"/api/games/{code}/properties/{prop['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    return code, host_id, host_token, prop


def test_net_worth_starts_as_just_cash(client):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    host = next(p for p in data["game"]["players"] if p["id"] == data["host_player_id"])
    assert host["net_worth"] == 1500


def test_net_worth_includes_unmortgaged_property_at_full_price(client):
    code, host_id, host_token, prop = _setup_owned_property(client)
    state = client.get(f"/api/games/{code}").json()
    host = next(p for p in state["players"] if p["id"] == host_id)
    assert host["net_worth"] == (1500 - 400) + 400  # cash spent, but the property is worth its price


def test_net_worth_counts_mortgaged_property_at_mortgage_value_not_zero(client):
    code, host_id, host_token, prop = _setup_owned_property(client)
    client.post(f"/api/games/{code}/properties/{prop['id']}/mortgage", headers={"x-player-id": host_id, "x-player-token": host_token})

    state = client.get(f"/api/games/{code}").json()
    host = next(p for p in state["players"] if p["id"] == host_id)
    # Cash: 1500 - 400 (purchase) + 200 (mortgage payout, 50% of 400) = 1300.
    # Net worth should count the mortgaged property at its mortgage value
    # (200), not drop it to zero the way the old estimate did.
    assert host["net_worth"] == 1300 + 200
