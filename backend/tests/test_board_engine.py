import pytest

from app.game_engine import board_generator, currency


def test_generator_satisfies_gap_constraints():
    tile_specs = [
        {"key": "a1", "group_key": "A", "locked_position": None},
        {"key": "a2", "group_key": "A", "locked_position": None},
        {"key": "e1", "group_key": "E", "locked_position": None},
        {"key": "e2", "group_key": "E", "locked_position": None},
        {"key": "e3", "group_key": "E", "locked_position": None},
        {"key": "e4", "group_key": "E", "locked_position": None},
        {"key": "misc", "group_key": None, "locked_position": None},
    ]
    layout = board_generator.generate_layout(
        board_size=24,
        corner_positions=[0, 6, 12, 18],
        tile_specs=tile_specs,
        group_constraints={"A": {"min_gap": 1, "max_gap": 3}, "E": {"min_gap": 4, "max_gap": 11}},
        seed=7,
    )
    assert set(layout.keys()) == {t["key"] for t in tile_specs}
    assert len(set(layout.values())) == len(tile_specs)  # no collisions
    for pos in layout.values():
        assert pos not in (0, 6, 12, 18)  # never on a corner

    a_gaps = board_generator._cluster_gaps(sorted([layout["a1"], layout["a2"]]), 24)
    assert all(g <= 3 for g in a_gaps)

    e_positions = sorted(layout[k] for k in ("e1", "e2", "e3", "e4"))
    e_gaps = board_generator._cluster_gaps(e_positions, 24)
    assert all(4 <= g <= 11 for g in e_gaps)


def test_generator_respects_locked_position():
    tile_specs = [
        {"key": "a1", "group_key": "A", "locked_position": 3},
        {"key": "a2", "group_key": "A", "locked_position": None},
    ]
    layout = board_generator.generate_layout(
        board_size=24, corner_positions=[0, 6, 12, 18], tile_specs=tile_specs,
        group_constraints={"A": {"min_gap": 1, "max_gap": 2}}, seed=1,
    )
    assert layout["a1"] == 3
    assert layout["a2"] in (1, 2, 4, 5)


def test_generator_raises_on_impossible_constraints():
    tile_specs = [{"key": f"x{i}", "group_key": "X", "locked_position": None} for i in range(4)]
    with pytest.raises(board_generator.BoardGenerationError):
        board_generator.generate_layout(
            board_size=8, corner_positions=[0, 2, 4, 6], tile_specs=tile_specs,
            group_constraints={"X": {"min_gap": 10, "max_gap": None}}, seed=1, max_attempts=20,
        )


def test_make_change_matches_spec_example():
    assert currency.make_change(70, [10, 20, 50, 100, 200, 500]) == {50: 1, 20: 1}


def test_make_change_rejects_unrepresentable_amount():
    with pytest.raises(currency.CurrencyError):
        currency.make_change(15, [10, 20, 50])  # no denomination combo sums to exactly 15


def test_apply_payment_moves_notes_and_returns_change():
    payer = {"200": 1}  # owes 130, tenders a 200, should get 50+20 back
    payee = {"50": 3, "20": 3, "10": 3}
    new_payer, new_payee = currency.apply_payment(payer, payee, 130, [10, 20, 50, 100, 200, 500])
    assert currency.total_of(new_payer) == 70
    assert currency.total_of(new_payee) == currency.total_of(payee) + 130


def test_apply_payment_rejects_insufficient_funds():
    with pytest.raises(currency.CurrencyError):
        currency.apply_payment({"10": 1}, {"10": 1}, 130, [10, 20, 50])


def _setup_current_game(client, **overrides):
    data = client.post(
        "/api/games", json={"host_name": "Alice", "board_key": "current_game", "banker_mode": "auto", **overrides}
    ).json()
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, host_id, host_token, bob["player_id"], bob["player_token"]


def test_list_and_fetch_boards(client):
    boards = client.get("/api/boards").json()
    keys = {b["key"] for b in boards}
    assert {"classic", "current_game"}.issubset(keys)

    detail = client.get("/api/boards/current_game").json()
    assert detail["size"] == 24
    assert len(detail["tiles"]) == 24
    assert len(detail["groups"]) == 5


def test_current_game_board_seeds_inr_currency_and_starting_cash(client):
    code, host_id, host_token, bob_id, bob_token = _setup_current_game(client)
    state = client.get(f"/api/games/{code}").json()
    assert state["board"]["key"] == "current_game"
    assert state["ruleset"]["currency"]["symbol"] == "₹"
    assert state["ruleset"]["starting_cash"] == 5000
    assert next(p for p in state["players"] if p["id"] == host_id)["balance"] == 5000
    assert len(state["properties"]) == 15


def test_group_rent_multiplier_applies_to_unimproved_full_group(client):
    code, host_id, host_token, bob_id, bob_token = _setup_current_game(client)
    state = client.get(f"/api/games/{code}").json()
    board = client.get("/api/boards/current_game").json()
    crown_group = next(g for g in board["groups"] if g["key"] == "A")
    crown_tiles = sorted([t for t in board["tiles"] if t["group_id"] == crown_group["id"]], key=lambda t: t["position"])
    assert len(crown_tiles) == 2

    crown_props = [next(p for p in state["properties"] if p["space_index"] == t["position"]) for t in crown_tiles]
    for prop in crown_props:
        client.post(
            f"/api/games/{code}/properties/{prop['id']}/purchase",
            headers={"x-player-id": host_id, "x-player-token": host_token},
        )

    base_rent = crown_tiles[0]["rent_table"][0]
    r = client.post(
        f"/api/games/{code}/land",
        json={"player_id": bob_id, "space_index": crown_tiles[0]["position"]},
        headers={"x-player-token": bob_token},
    )
    assert r.json()["outcome"]["outcome"] == "rent_paid"
    assert r.json()["outcome"]["amount"] == base_rent * 2  # full unimproved group doubles rent
