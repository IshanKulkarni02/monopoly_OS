def _setup_game_with_brown_monopoly(client, **overrides):
    data = client.post("/api/games", json={"host_name": "Alice", **overrides}).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    state = client.get(f"/api/games/{code}").json()
    med_ave = next(p for p in state["properties"] if p["name"] == "Mediterranean Avenue")
    baltic_ave = next(p for p in state["properties"] if p["name"] == "Baltic Avenue")
    return code, host_id, host_token, bob["player_id"], bob["player_token"], med_ave, baltic_ave


def test_cannot_build_without_full_color_group(client):
    code, host_id, host_token, *_rest, med_ave, baltic_ave = _setup_game_with_brown_monopoly(client)
    client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/purchase",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )

    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 400


def test_build_house_after_owning_full_group(client):
    code, host_id, host_token, *_rest, med_ave, baltic_ave = _setup_game_with_brown_monopoly(client)
    for prop in (med_ave, baltic_ave):
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )

    balance_before = client.get(f"/api/games/{code}").json()
    host_before = next(p for p in balance_before["players"] if p["id"] == host_id)["balance"]

    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200
    state = r.json()
    host_after = next(p for p in state["players"] if p["id"] == host_id)["balance"]
    assert host_after == host_before - 50  # brown group house cost
    med_after = next(p for p in state["properties"] if p["id"] == med_ave["id"])
    assert med_after["houses"] == 1


def test_even_building_rule_enforced(client):
    code, host_id, host_token, *_rest, med_ave, baltic_ave = _setup_game_with_brown_monopoly(client)
    for prop in (med_ave, baltic_ave):
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )

    client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    # Med now has 1 house, Baltic has 0 -> building on Med again should be rejected
    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 400

    # Building on Baltic to even things out should succeed
    r = client.post(
        f"/api/games/{code}/properties/{baltic_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200


def test_build_up_to_hotel_then_blocked(client):
    code, host_id, host_token, *_rest, med_ave, baltic_ave = _setup_game_with_brown_monopoly(client)
    for prop in (med_ave, baltic_ave):
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )

    for _ in range(5):
        for prop in (med_ave, baltic_ave):
            r = client.post(
                f"/api/games/{code}/properties/{prop['id']}/build_house",
                headers={"x-player-id": host_id, "x-player-token": host_token},
            )
            assert r.status_code == 200

    state = r.json()
    med_after = next(p for p in state["properties"] if p["id"] == med_ave["id"])
    assert med_after["houses"] == 5  # hotel

    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 400


def test_sell_house_refunds_half_and_enforces_even_selling(client):
    code, host_id, host_token, *_rest, med_ave, baltic_ave = _setup_game_with_brown_monopoly(client)
    for prop in (med_ave, baltic_ave):
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )
    # Build 2 houses on each
    for _ in range(2):
        for prop in (med_ave, baltic_ave):
            client.post(
                f"/api/games/{code}/properties/{prop['id']}/build_house",
                headers={"x-player-id": host_id, "x-player-token": host_token},
            )

    balance_before = client.get(f"/api/games/{code}").json()
    host_before = next(p for p in balance_before["players"] if p["id"] == host_id)["balance"]

    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/sell_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 200
    state = r.json()
    host_after = next(p for p in state["players"] if p["id"] == host_id)["balance"]
    assert host_after == host_before + 25  # half of $50
    med_after = next(p for p in state["properties"] if p["id"] == med_ave["id"])
    assert med_after["houses"] == 1

    # Med now has 1, Baltic has 2 -> selling from Med again would go below the group max unevenly
    r = client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/sell_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    assert r.status_code == 400


def test_rent_auto_calculation_scales_with_houses(client):
    code, host_id, host_token, bob_id, bob_token, med_ave, baltic_ave = _setup_game_with_brown_monopoly(
        client, banker_mode="auto"
    )
    for prop in (med_ave, baltic_ave):
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )
    client.post(
        f"/api/games/{code}/properties/{med_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )
    client.post(
        f"/api/games/{code}/properties/{baltic_ave['id']}/build_house",
        headers={"x-player-id": host_id, "x-player-token": host_token},
    )

    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": 1},  # Mediterranean Avenue, now with 1 house
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "rent_paid"
    assert r.json()["outcome"]["amount"] == 10  # rent[1] for Mediterranean Avenue
