from dataclasses import dataclass


@dataclass
class EventOutcome:
    # bank_pays | pay_bank | pay_each_player | collect_each_player | jail_free | pass_go |
    # move_forward | move_backward | move_to | lose_turn | extra_turn | nothing
    kind: str
    amount: int
    text: str
    target_position: int | None = None  # move_to only
