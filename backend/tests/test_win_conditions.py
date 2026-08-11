def _setup_game(client, num_players=2):
    data = client.post("/api/games", json={"host_name": "Alice"}).json()
    code = data["game"]["code"]
    players = [{"id": data["host_player_id"], "token": data["player_token"]}]
    for name in ["Bob", "Carol"][: num_players - 1]:
        r = client.post(f"/api/games/{code}/join", json={"name": name}).json()
        players.append({"id": r["player_id"], "token": r["player_token"]})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})
    return code, players


def _headers(p):
    return {"x-player-id": p["id"], "x-player-token": p["token"]}


def test_game_does_not_end_while_two_or_more_players_are_active(client):
    code, players = _setup_game(client, num_players=3)
    alice, bob, carol = players
    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 200
    state = r.json()
    assert state["status"] == "active"
    assert state["winner_player_id"] is None


def test_last_player_standing_wins_and_game_ends(client):
    code, players = _setup_game(client, num_players=2)
    alice, bob = players
    r = client.post(f"/api/games/{code}/declare_bankruptcy", json={}, headers=_headers(alice))
    assert r.status_code == 200
    state = r.json()
    assert state["status"] == "ended"
    assert state["winner_player_id"] == bob["id"]

    log_kinds = [e["kind"] for e in state["recent_log"]]
    assert "game_over" in log_kinds


def test_two_player_game_never_auto_wins_before_anyone_goes_bankrupt(client):
    code, players = _setup_game(client, num_players=2)
    state = client.get(f"/api/games/{code}").json()
    assert state["status"] == "active"
    assert state["winner_player_id"] is None
