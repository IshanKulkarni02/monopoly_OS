from dataclasses import dataclass


@dataclass
class EventOutcome:
    kind: str  # bank_pays | pay_bank | pay_each_player | collect_each_player | jail_free | pass_go | nothing
    amount: int
    text: str
