def _signed_in_user(client, email="mystery@example.com"):
    return client.post("/api/auth/signup", json={"email": email, "password": "password1", "name": "GM"}).json()


def test_list_mystery_cards_for_preset_board_is_public(client):
    r = client.get("/api/boards/classic/mystery_cards", params={"deck_key": "chance"})
    assert r.status_code == 200
    cards = r.json()
    assert len(cards) > 0
    assert all(c["deck_key"] == "chance" for c in cards)


def test_create_mystery_card_requires_ownership(client):
    r = client.post(
        "/api/boards/classic/mystery_cards",
        json={"deck_key": "chance", "text": "Hack", "effect_kind": "bank_pays", "amount": 999999},
    )
    assert r.status_code == 401


def test_create_update_delete_mystery_card_on_owned_board(client):
    auth = _signed_in_user(client)
    client.post(
        "/api/boards/current_game/duplicate",
        json={"key": "mystery-test-board", "name": "Mystery Test", "description": ""},
        headers={"x-session-token": auth["session_token"]},
    )

    r = client.post(
        "/api/boards/mystery-test-board/mystery_cards",
        json={"deck_key": "mystery", "text": "Win the lottery", "effect_kind": "bank_pays", "amount": 500},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200, r.text
    card = r.json()
    assert card["text"] == "Win the lottery"
    assert card["amount"] == 500

    r = client.patch(
        f"/api/boards/mystery-test-board/mystery_cards/{card['id']}",
        json={"amount": 750},
        headers={"x-session-token": auth["session_token"]},
    )
    assert r.status_code == 200
    assert r.json()["amount"] == 750

    r = client.delete(f"/api/boards/mystery-test-board/mystery_cards/{card['id']}", headers={"x-session-token": auth["session_token"]})
    assert r.status_code == 200
    remaining = client.get("/api/boards/mystery-test-board/mystery_cards", params={"deck_key": "mystery"}).json()
    assert card["id"] not in [c["id"] for c in remaining]


def test_finite_deck_mode_draws_without_replacement(client, monkeypatch):
    # Force a tiny, fully-controlled deck so exhaustion is reachable in a
    # small number of draws.
    from app.game_engine import mystery as mystery_engine

    class FakeCard:
        def __init__(self, id, effect_kind, amount, text):
            self.id = id
            self.effect_kind = effect_kind
            self.amount = amount
            self.text = text
            self.target_position = None
            self.deck_key = "chance"

    fake_cards = [FakeCard(f"c{i}", "bank_pays", 10, f"card {i}") for i in range(3)]
    monkeypatch.setattr(mystery_engine, "cards_for_deck", lambda db, board_id, deck_key: fake_cards)

    data = client.post("/api/games", json={"host_name": "Alice", "mystery_deck_mode": "finite"}).json()
    assert data["game"]["ruleset"]["mystery_deck_mode"] == "finite"
    code = data["game"]["code"]
    host_id = data["host_player_id"]
    host_token = data["player_token"]
    client.post(f"/api/games/{code}/join", json={"name": "Bob"})
    client.post(f"/api/games/{code}/start", headers={"x-host-token": data["host_token"]})

    drawn_texts = []
    for _ in range(3):
        r = client.post(
            f"/api/games/{code}/draw_event",
            json={"player_id": host_id, "space_index": 7},
            headers={"x-player-token": host_token},
        )
        assert r.status_code == 200
        drawn_texts.append(r.json()["outcome"]["text"])

    # exactly 3 distinct cards drawn across exactly 3 draws -> no replacement
    assert sorted(drawn_texts) == ["card 0", "card 1", "card 2"]


def test_finite_deck_engine_exhausts_and_reshuffles_without_immediate_repeat_when_possible():
    from types import SimpleNamespace

    from app.game_engine import mystery as mystery_engine

    cards = [SimpleNamespace(id=f"c{i}") for i in range(3)]
    game = SimpleNamespace(mystery_deck_state={}, ruleset_json={"mystery_deck_mode": "finite"})

    drawn_order = []
    for _ in range(6):  # two full passes through a 3-card deck
        card = mystery_engine._draw_finite(game, "chance", cards)
        drawn_order.append(card.id)

    first_pass, second_pass = drawn_order[:3], drawn_order[3:]
    assert sorted(first_pass) == ["c0", "c1", "c2"]  # every card drawn exactly once per pass
    assert sorted(second_pass) == ["c0", "c1", "c2"]
