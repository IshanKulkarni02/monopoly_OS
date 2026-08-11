from app.game_engine import simulation


def test_simulate_one_game_via_engine_function_leaves_no_row_behind(client):
    from app.db import SessionLocal
    from app.models import Game

    db = SessionLocal()
    try:
        before = db.query(Game).count()
        result = simulation.simulate_one_game(db, board_key="classic", ruleset_overrides=None, num_bots=2, max_turns=80)
        after = db.query(Game).count()
        assert after == before  # the simulated game was cleaned up
        assert result["player_count"] == 2
        assert result["turns_played"] <= 80
        assert len(result["final_net_worths"]) == 2
    finally:
        db.close()


def test_simulate_endpoint_returns_aggregate_stats(client):
    r = client.post(
        "/api/simulate",
        json={"board_key": "classic", "num_games": 2, "num_bots": 2, "max_turns": 80},
    )
    assert r.status_code == 200, r.text
    agg = r.json()
    assert agg["games_played"] == 2
    assert "win_rate_by_starting_position" in agg
    assert "average_turns_played" in agg


def test_simulate_rejects_unknown_board(client):
    r = client.post("/api/simulate", json={"board_key": "no-such-board", "num_games": 1, "num_bots": 2, "max_turns": 50})
    assert r.status_code == 400


def test_simulate_rejects_too_few_bots(client):
    r = client.post("/api/simulate", json={"board_key": "classic", "num_games": 1, "num_bots": 1, "max_turns": 50})
    assert r.status_code == 422  # num_bots has a ge=2 constraint


def test_simulate_compare_returns_baseline_and_variant(client):
    r = client.post(
        "/api/simulate/compare",
        json={
            "board_key": "classic",
            "baseline_overrides": {},
            "variant_overrides": {"starting_cash": 3000},
            "num_games": 1,
            "num_bots": 2,
            "max_turns": 80,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "baseline" in body and "variant" in body
    assert body["baseline"]["games_played"] == 1
    assert body["variant"]["games_played"] == 1


def test_landing_probabilities_sum_to_one_and_favor_jail(client):
    r = client.get("/api/boards/classic/landing_probabilities")
    assert r.status_code == 200
    tiles = r.json()["tiles"]
    total = sum(t["probability"] for t in tiles)
    assert abs(total - 1.0) < 0.001

    jail = next(t for t in tiles if t["kind"] == "jail")
    average = 1 / len(tiles)
    assert jail["probability"] > average * 1.5  # jail is famously landed on far more than average


def test_landing_probabilities_unknown_board_404s(client):
    r = client.get("/api/boards/no-such-board/landing_probabilities")
    assert r.status_code == 404
