"""Constraint-based board layout generator (spec §4).

Produces a position assignment for a board's non-corner tiles given:
- the total board size (corners occupy their own fixed positions)
- a pool of non-corner tile specs (properties grouped, mystery, tax, ...)
- per-group spacing constraints: `min_gap` / `max_gap` between consecutive
  members of the same group, measured going around the board
- optional locked positions for specific tile specs, set before randomizing

This is randomized placement with retries, not a full CSP solver — that's a
deliberate simplification: the group counts and board sizes this engine
targets are small (dozens of tiles, single-digit group sizes), where
randomize-and-check converges fast and stays easy to reason about and test.
Tiles with no group (mystery, tax, custom singles) place freely with no
spacing constraint against each other.
"""

import random


class BoardGenerationError(Exception):
    pass


def _circular_gaps(positions: list[int], board_size: int) -> list[int]:
    if len(positions) < 2:
        return []
    ordered = sorted(positions)
    gaps = [b - a for a, b in zip(ordered, ordered[1:])]
    gaps.append(board_size - ordered[-1] + ordered[0])
    return gaps


def _cluster_gaps(positions: list[int], board_size: int) -> list[int]:
    """Gaps *within* the group's own span, excluding the one large arc that
    wraps back around through the rest of the board — that outside arc isn't
    a "gap between members," it's everything that isn't this group. All of a
    circle's gaps necessarily sum to `board_size`, so treating every gap
    (including that leftover arc) as bounded by `max_gap` is unsatisfiable
    for any cluster smaller than the whole board; dropping the largest one
    is what actually captures "these members sit close together."
    """
    gaps = _circular_gaps(positions, board_size)
    if len(gaps) <= 1:
        return gaps
    ordered = sorted(gaps)
    return ordered[:-1]


def _place_group(
    free: list[int],
    count: int,
    already_placed: list[int],
    board_size: int,
    min_gap: int | None,
    max_gap: int | None,
    rng: random.Random,
    tries: int = 300,
) -> list[int] | None:
    if count == 0:
        return []
    for _ in range(tries):
        pick = rng.sample(free, count)
        candidate = sorted(already_placed + pick)
        gaps = _cluster_gaps(candidate, board_size)
        if gaps:
            if min_gap is not None and min(gaps) < min_gap:
                continue
            if max_gap is not None and max(gaps) > max_gap:
                continue
        return pick
    return None


def generate_layout(
    *,
    board_size: int,
    corner_positions: list[int],
    tile_specs: list[dict],
    group_constraints: dict[str, dict] | None = None,
    seed: int | None = None,
    max_attempts: int = 200,
) -> dict[str, int]:
    """Returns `{tile_spec_key: position}` for every spec in `tile_specs`.

    `tile_specs`: each `{"key": str, "group_key": str | None, "locked_position": int | None}`.
    `group_constraints`: `group_key -> {"min_gap": int | None, "max_gap": int | None}`.
    Groups placed tightest-first (smallest `max_gap`) so the hardest
    constraints get first pick of the position pool.
    """
    group_constraints = group_constraints or {}
    rng = random.Random(seed)
    non_corner = [p for p in range(board_size) if p not in corner_positions]

    locked: dict[str, int] = {t["key"]: t["locked_position"] for t in tile_specs if t.get("locked_position") is not None}
    for key, pos in locked.items():
        if pos not in non_corner:
            raise BoardGenerationError(f"Locked position {pos} for '{key}' is not a valid non-corner tile slot")

    spec_group = {t["key"]: t.get("group_key") for t in tile_specs}
    groups: dict[str | None, list[str]] = {}
    for t in tile_specs:
        groups.setdefault(t.get("group_key"), []).append(t["key"])

    grouped_keys = sorted(
        (g for g in groups if g is not None),
        key=lambda g: group_constraints.get(g, {}).get("max_gap") or board_size,
    )
    ungrouped_keys = groups.get(None, [])

    for _attempt in range(max_attempts):
        assignment = dict(locked)
        free = [p for p in non_corner if p not in assignment.values()]
        rng.shuffle(free)
        ok = True

        for group_key in grouped_keys:
            keys = [k for k in groups[group_key] if k not in assignment]
            if not keys:
                continue
            constraint = group_constraints.get(group_key, {})
            already = [assignment[k] for k in groups[group_key] if k in assignment]
            placed = _place_group(
                free, len(keys), already, board_size,
                constraint.get("min_gap"), constraint.get("max_gap"), rng,
            )
            if placed is None:
                ok = False
                break
            for k, pos in zip(keys, placed):
                assignment[k] = pos
                free.remove(pos)

        if not ok:
            continue

        for key in ungrouped_keys:
            if key in assignment:
                continue
            if not free:
                ok = False
                break
            pos = free.pop(rng.randrange(len(free)))
            assignment[key] = pos

        if ok and len(assignment) == len(tile_specs):
            return assignment

    raise BoardGenerationError(
        "Could not generate a layout satisfying the configured spacing constraints "
        "after multiple attempts — try relaxing min_gap/max_gap."
    )
