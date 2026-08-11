def test_signup_login_and_me(client):
    r = client.post("/api/auth/signup", json={"email": "Alice@Example.com", "password": "hunter22", "name": "Alice"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "alice@example.com"
    token = body["session_token"]

    r = client.get("/api/auth/me", headers={"x-session-token": token})
    assert r.status_code == 200
    assert r.json()["name"] == "Alice"

    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "hunter22"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "alice@example.com"


def test_signup_rejects_duplicate_email(client):
    client.post("/api/auth/signup", json={"email": "bob@example.com", "password": "password1", "name": "Bob"})
    r = client.post("/api/auth/signup", json={"email": "bob@example.com", "password": "password2", "name": "Bob2"})
    assert r.status_code == 400


def test_login_rejects_wrong_password(client):
    client.post("/api/auth/signup", json={"email": "carl@example.com", "password": "correcthorse", "name": "Carl"})
    r = client.post("/api/auth/login", json={"email": "carl@example.com", "password": "wrongpassword"})
    assert r.status_code == 401


def test_me_requires_session(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_logout_invalidates_session(client):
    data = client.post("/api/auth/signup", json={"email": "dana@example.com", "password": "password1", "name": "Dana"}).json()
    token = data["session_token"]
    client.post("/api/auth/logout", headers={"x-session-token": token})
    r = client.get("/api/auth/me", headers={"x-session-token": token})
    assert r.status_code == 401


def test_game_created_while_logged_in_is_owned_by_user(client):
    auth = client.post("/api/auth/signup", json={"email": "erin@example.com", "password": "password1", "name": "Erin"}).json()
    r = client.post(
        "/api/games",
        json={"host_name": "Erin"},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200
    # ownership isn't in GameStateOut, but saving a board template (which requires it) should work
    code = r.json()["game"]["code"]
    host_token = r.json()["host_token"]
    bob = client.post(f"/api/games/{code}/join", json={"name": "Bob"}).json()
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    r = client.post(
        f"/api/games/{code}/save_board_template",
        json={"key": "eriens-template", "name": "Erin's Template", "description": "test"},
        headers={"x-host-token": host_token, "x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200
    assert r.json()["key"] == "eriens-template"
    del bob


def test_saving_a_board_template_from_a_live_game_captures_the_whole_preset(client):
    auth = client.post("/api/auth/signup", json={"email": "priya@example.com", "password": "password1", "name": "Priya"}).json()
    data = client.post(
        "/api/games",
        json={"host_name": "Priya", "play_mode": "virtual", "banker_mode": "auto", "auction_enabled": True},
        headers={"x-session-token": auth["session_token"]},
    ).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Sam"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    r = client.post(
        f"/api/games/{code}/save_board_template",
        json={"key": "priyas-preset", "name": "Priya's Preset", "description": "virtual + auctions"},
        headers={"x-host-token": host_token, "x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200
    board = r.json()
    assert board["preset_play_options"] == {"play_mode": "virtual", "banker_mode": "auto", "money_mode": "banker_ledger"}
    assert board["default_ruleset_overrides"]["auction_enabled"] is True


def test_save_board_template_requires_login(client):
    data = client.post("/api/games", json={"host_name": "Frank"}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Gary"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})

    r = client.post(
        f"/api/games/{code}/save_board_template",
        json={"key": "franks-template", "name": "Frank's Template", "description": ""},
        headers={"x-host-token": host_token},
    )
    assert r.status_code == 401


def test_board_list_includes_new_presets(client):
    keys = {b["key"] for b in client.get("/api/boards").json()}
    assert {"classic", "indian", "european", "current_game"}.issubset(keys)


def test_custom_board_only_visible_to_owner(client):
    alice = client.post("/api/auth/signup", json={"email": "helen@example.com", "password": "password1", "name": "Helen"}).json()
    data = client.post("/api/games", json={"host_name": "Helen"}, headers={"x-session-token": alice["session_token"]}).json()
    code = data["game"]["code"]
    host_token = data["host_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": host_token})
    client.post(
        f"/api/games/{code}/save_board_template",
        json={"key": "helens-secret-board", "name": "Helens Board", "description": ""},
        headers={"x-host-token": host_token, "x-session-token": alice["session_token"]},
    )

    anon_keys = {b["key"] for b in client.get("/api/boards").json()}
    assert "helens-secret-board" not in anon_keys

    owner_keys = {b["key"] for b in client.get("/api/boards", headers={"x-session-token": alice["session_token"]}).json()}
    assert "helens-secret-board" in owner_keys
