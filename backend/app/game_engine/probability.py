"""Landing-probability analysis — a purely mathematical property of a board
(given its tile layout and dice count, what's the steady-state chance of
landing on each tile), computed via a Markov chain over board positions.
No actual gameplay involved, unlike `simulation.py`.

Deliberately a simplification: models forward movement by dice roll and the
`go_to_jail` redirect, but not jail's stay-a-few-turns dynamics or mystery
cards' move effects (those are conditional on card draws and player
choices, not a fixed transition) — modeling those exactly would turn this
into a full simulation rather than a closed-form board property. This still
answers the design question that matters: "given how tiles are spaced
around this board, which ones get landed on most?"
"""

from sqlalchemy.orm import Session

from app.models import Board


class ProbabilityError(Exception):
    pass


def dice_sum_distribution(dice_count: int) -> dict[int, float]:
    """Probability of each possible sum of `dice_count` six-sided dice, via
    repeated convolution — generalizes past the classic 2-die case to
    whatever `dice_count` a ruleset configures (this engine supports 1-4)."""
    dist = {0: 1.0}
    for _ in range(dice_count):
        next_dist: dict[int, float] = {}
        for total, prob in dist.items():
            for face in range(1, 7):
                next_dist[total + face] = next_dist.get(total + face, 0.0) + prob / 6
        dist = next_dist
    return dist


def compute_landing_probabilities(db: Session, board: Board, *, dice_count: int = 2, iterations: int = 300) -> list[dict]:
    tiles = sorted(board.tiles, key=lambda t: t.position)
    size = len(tiles)
    if size == 0:
        raise ProbabilityError("Board has no tiles")

    roll_dist = dice_sum_distribution(dice_count)
    jail_tile = next((t for t in tiles if t.kind == "jail"), None)
    jail_position = jail_tile.position if jail_tile else 0

    # transitions[i] = list of (destination_position, probability) pairs
    transitions: list[list[tuple[int, float]]] = []
    for tile in tiles:
        if tile.kind == "go_to_jail":
            transitions.append([(jail_position, 1.0)])
            continue
        row: dict[int, float] = {}
        for roll, prob in roll_dist.items():
            dest = (tile.position + roll) % size
            row[dest] = row.get(dest, 0.0) + prob
        transitions.append(list(row.items()))

    probs = [1.0 / size] * size
    for _ in range(iterations):
        next_probs = [0.0] * size
        for i, row in enumerate(transitions):
            p_i = probs[i]
            for dest, p in row:
                next_probs[dest] += p_i * p
        probs = next_probs

    return [
        {"position": t.position, "name": t.name, "kind": t.kind, "probability": round(probs[i], 5)}
        for i, t in enumerate(tiles)
    ]
