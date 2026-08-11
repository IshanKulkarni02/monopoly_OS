"""Currency/denomination helpers (spec §7).

A game's denomination list lives at `ruleset_json["currency"]["denominations"]`
(largest to smallest isn't required — these functions sort internally).
Standard real-world denomination sets (which is all this engine ever seeds)
are "canonical" for greedy change-making, so a simple largest-first pass is
optimal here; a full dynamic-programming coin-change isn't needed.
"""


class CurrencyError(Exception):
    pass


def make_change(amount: int, denominations: list[int]) -> dict[int, int]:
    """Greedy largest-first breakdown of `amount` into denomination counts.

    Raises `CurrencyError` if `amount` can't be represented exactly by the
    given denominations (e.g. an odd amount with only even notes).
    """
    if amount < 0:
        raise CurrencyError("Amount must be non-negative")
    remaining = amount
    breakdown: dict[int, int] = {}
    for note in sorted({d for d in denominations if d > 0}, reverse=True):
        count, remaining = divmod(remaining, note)
        if count:
            breakdown[note] = count
    if remaining != 0:
        raise CurrencyError(f"{amount} cannot be represented exactly with denominations {denominations}")
    return breakdown


def total_of(denomination_counts: dict[str, int] | dict[int, int]) -> int:
    return sum(int(denom) * count for denom, count in denomination_counts.items())


def seed_denominations(amount: int, denominations: list[int]) -> dict[str, int]:
    """Break a starting balance into notes for a new player/bank, largest-first.
    Any leftover that isn't evenly representable is folded into the smallest
    denomination's count so the total still balances exactly."""
    if not denominations:
        return {}
    breakdown = {}
    remaining = amount
    sorted_denoms = sorted(set(denominations), reverse=True)
    smallest = sorted_denoms[-1]
    for note in sorted_denoms[:-1]:
        count, remaining = divmod(remaining, note)
        if count:
            breakdown[note] = count
    leftover_notes, remainder = divmod(remaining, smallest)
    if leftover_notes:
        breakdown[smallest] = breakdown.get(smallest, 0) + leftover_notes
    if remainder:
        # Not evenly representable in the smallest note — round up by one
        # note rather than silently dropping value.
        breakdown[smallest] = breakdown.get(smallest, 0) + 1
    return {str(k): v for k, v in breakdown.items()}


def can_pay(denomination_counts: dict[str, int], amount: int) -> bool:
    return total_of(denomination_counts) >= amount


def apply_payment(
    payer_counts: dict[str, int], payee_counts: dict[str, int], amount: int, denominations: list[int]
) -> tuple[dict[str, int], dict[str, int]]:
    """Move `amount` from payer to payee, tendering the fewest large notes
    that cover it and returning change from the payee's own notes. Raises
    `CurrencyError` if the payer can't cover the amount at all, or if exact
    change isn't achievable from what's on hand (a real "impossible payment"
    per spec §7, not just a shortfall in total value).
    """
    if not can_pay(payer_counts, amount):
        raise CurrencyError("Payer does not have enough cash to cover this amount")

    payer = {int(k): v for k, v in payer_counts.items()}
    payee = {int(k): v for k, v in payee_counts.items()}

    tendered = 0
    used: dict[int, int] = {}
    for note in sorted(payer.keys(), reverse=True):
        if tendered >= amount:
            break
        available = payer[note]
        needed = -(-(amount - tendered) // note)  # ceil
        take = min(available, needed)
        if take:
            used[note] = take
            tendered += take * note

    if tendered < amount:
        raise CurrencyError("Payer's notes cannot cover this amount even combined")

    change_due = tendered - amount
    change = make_change(change_due, list(payee.keys()) or denominations) if change_due else {}
    if any(payee.get(note, 0) < count for note, count in change.items()):
        raise CurrencyError("Cannot make exact change with the notes currently on hand")

    for note, count in used.items():
        payer[note] -= count
        payee[note] = payee.get(note, 0) + count
    for note, count in change.items():
        payee[note] -= count
        payer[note] = payer.get(note, 0) + count

    payer = {str(k): v for k, v in payer.items() if v}
    payee = {str(k): v for k, v in payee.items() if v}
    return payer, payee
