def _signed_in_user(client, email="editor@example.com"):
    return client.post("/api/auth/signup", json={"email": email, "password": "password1", "name": "Editor"}).json()


def _duplicate(client, token, source_key="current_game", key="my-board"):
    r = client.post(
        f"/api/boards/{source_key}/duplicate",
        json={"key": key, "name": "My Board", "description": "test board"},
        headers={"x-session-token": token},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_duplicate_requires_login(client):
    r = client.post("/api/boards/current_game/duplicate", json={"key": "x", "name": "X", "description": ""})
    assert r.status_code == 401


def test_duplicate_creates_owned_copy(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    assert board["key"] == "my-board"
    assert board["is_preset"] is False
    assert len(board["tiles"]) == 24
    assert len(board["groups"]) == 5


def test_cannot_duplicate_into_existing_key(client):
    auth = _signed_in_user(client)
    _duplicate(client, auth["session_token"])
    r = client.post(
        "/api/boards/current_game/duplicate",
        json={"key": "my-board", "name": "Dup", "description": ""},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 400


def test_cannot_edit_a_preset_board(client):
    auth = _signed_in_user(client)
    r = client.patch(
        "/api/boards/classic", json={"name": "Hacked"}, headers={"x-session-token": auth["session_token"]}
    )
    assert r.status_code == 403


def test_cannot_edit_someone_elses_board(client):
    owner = _signed_in_user(client, "owner@example.com")
    _duplicate(client, owner["session_token"])
    other = _signed_in_user(client, "other@example.com")
    r = client.patch(
        "/api/boards/my-board", json={"name": "Hijacked"}, headers={"x-session-token": other["session_token"]}
    )
    assert r.status_code == 403


def test_rename_owned_board(client):
    auth = _signed_in_user(client)
    _duplicate(client, auth["session_token"])
    r = client.patch(
        "/api/boards/my-board", json={"name": "Renamed"}, headers={"x-session-token": auth["session_token"]}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"


def test_insert_tile_shifts_positions_and_grows_board(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    tile_at_1_before = next(t for t in board["tiles"] if t["position"] == 1)

    r = client.post(
        "/api/boards/my-board/tiles",
        json={"position": 1, "name": "New Tile", "kind": "custom"},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["size"] == 25
    assert len(updated["tiles"]) == 25
    new_tile = next(t for t in updated["tiles"] if t["position"] == 1)
    assert new_tile["name"] == "New Tile"
    moved_tile = next(t for t in updated["tiles"] if t["id"] == tile_at_1_before["id"])
    assert moved_tile["position"] == 2
    # every position 0..size-1 is occupied exactly once
    assert sorted(t["position"] for t in updated["tiles"]) == list(range(25))


def test_remove_tile_shifts_positions_and_shrinks_board(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    tile_to_remove = next(t for t in board["tiles"] if t["position"] == 3)
    tile_after = next(t for t in board["tiles"] if t["position"] == 4)

    r = client.delete(f"/api/boards/my-board/tiles/{tile_to_remove['id']}", headers={"x-session-token": auth["session_token"]})
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["size"] == 23
    assert len(updated["tiles"]) == 23
    assert not any(t["id"] == tile_to_remove["id"] for t in updated["tiles"])
    moved = next(t for t in updated["tiles"] if t["id"] == tile_after["id"])
    assert moved["position"] == 3
    assert sorted(t["position"] for t in updated["tiles"]) == list(range(23))


def test_cannot_shrink_board_below_four_tiles(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    # remove down to 4 tiles
    while len(board["tiles"]) > 4:
        victim = board["tiles"][-1]
        r = client.delete(f"/api/boards/my-board/tiles/{victim['id']}", headers={"x-session-token": auth["session_token"]})
        board = r.json()

    last = board["tiles"][0]
    r = client.delete(f"/api/boards/my-board/tiles/{last['id']}", headers={"x-session-token": auth["session_token"]})
    assert r.status_code == 400


def test_update_tile_fields(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    tile = next(t for t in board["tiles"] if t["kind"] == "property")

    r = client.patch(
        f"/api/boards/my-board/tiles/{tile['id']}",
        json={"name": "Renamed Property", "price": 999},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    updated_tile = next(t for t in r.json()["tiles"] if t["id"] == tile["id"])
    assert updated_tile["name"] == "Renamed Property"
    assert updated_tile["price"] == 999


def test_update_tile_rejects_invalid_kind(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    tile = board["tiles"][0]
    r = client.patch(
        f"/api/boards/my-board/tiles/{tile['id']}",
        json={"kind": "not_a_real_kind"},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 400


def test_move_tile_swaps_positions(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    tile_a = next(t for t in board["tiles"] if t["position"] == 2)
    tile_b = next(t for t in board["tiles"] if t["position"] == 5)

    r = client.post(
        f"/api/boards/my-board/tiles/{tile_a['id']}/move",
        json={"other_tile_id": tile_b["id"]},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    assert next(t for t in updated["tiles"] if t["id"] == tile_a["id"])["position"] == 5
    assert next(t for t in updated["tiles"] if t["id"] == tile_b["id"])["position"] == 2


def test_create_and_update_group(client):
    auth = _signed_in_user(client)
    _duplicate(client, auth["session_token"])

    r = client.post(
        "/api/boards/my-board/groups",
        json={"key": "Z", "name": "Zeta", "color": "#123456"},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    group = next(g for g in r.json()["groups"] if g["key"] == "Z")
    assert group["name"] == "Zeta"

    r = client.patch(
        f"/api/boards/my-board/groups/{group['id']}",
        json={"name": "Zeta Renamed", "rent_multiplier": 3.0},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200
    updated_group = next(g for g in r.json()["groups"] if g["id"] == group["id"])
    assert updated_group["name"] == "Zeta Renamed"
    assert updated_group["rent_multiplier"] == 3.0


def test_regenerate_layout_respects_locked_tiles(client):
    auth = _signed_in_user(client)
    board = _duplicate(client, auth["session_token"])
    property_tile = next(t for t in board["tiles"] if t["kind"] == "property")

    client.patch(
        f"/api/boards/my-board/tiles/{property_tile['id']}",
        json={"locked": True},
        headers={"x-session-token": auth["session_token"]},
    )

    r = client.post(
        "/api/boards/my-board/generate",
        json={"group_constraints": {}, "seed": 123},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    updated = r.json()
    locked_after = next(t for t in updated["tiles"] if t["id"] == property_tile["id"])
    assert locked_after["position"] == property_tile["position"]
    # every position still occupied exactly once after regeneration
    assert sorted(t["position"] for t in updated["tiles"]) == list(range(updated["size"]))
    # corners never move
    corner_kinds = {"go", "jail", "vacation", "go_to_jail"}
    corners_before = {t["position"]: t["kind"] for t in board["tiles"] if t["kind"] in corner_kinds}
    corners_after = {t["position"]: t["kind"] for t in updated["tiles"] if t["kind"] in corner_kinds}
    assert corners_before == corners_after


def test_delete_board(client):
    auth = _signed_in_user(client)
    _duplicate(client, auth["session_token"])
    r = client.delete("/api/boards/my-board", headers={"x-session-token": auth["session_token"]})
    assert r.status_code == 200
    assert client.get("/api/boards/my-board").status_code == 404


def test_cannot_delete_preset_board(client):
    auth = _signed_in_user(client)
    r = client.delete("/api/boards/classic", headers={"x-session-token": auth["session_token"]})
    assert r.status_code in (400, 403)
