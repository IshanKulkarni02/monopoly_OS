from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(default="", max_length=60)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str


class AuthResponse(BaseModel):
    user: UserOut
    session_token: str


class GameCreateRequest(BaseModel):
    host_name: str = Field(min_length=1, max_length=40)
    name: str = Field(default="Monopoly Night", max_length=60)
    board_key: str | None = None
    starting_cash: int | None = Field(default=None, ge=0)
    banker_mode: Literal["manual", "auto"] = "manual"
    play_mode: Literal["irl_companion", "virtual"] = "irl_companion"
    money_mode: Literal["banker_ledger", "cash_counter", "digital_transfer"] = "banker_ledger"
    event_system: Literal["cards", "wheel"] = "cards"
    free_parking_pot: bool = False
    challenge_before_buy: bool = False
    inflation_enabled: bool = False
    inflation_trigger: Literal["on_pass_go", "per_round"] = "on_pass_go"
    inflation_rate: float = Field(default=0.0, ge=0, le=1)
    dice_count: int = Field(default=2, ge=1, le=4)
    turn_order_mode: Literal["highest_roll_first", "entry_order"] = "highest_roll_first"


class JoinGameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class AddPlayerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    is_host: bool
    is_banker: bool
    is_bot: bool
    balance: int
    denominations: dict[str, int] = {}
    status: str
    jail_free_cards: int
    position: int
    in_jail: bool
    jail_turns: int


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    space_index: int
    name: str
    owner_id: str | None
    price: int
    houses: int
    mortgaged: bool


class BoardGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    name: str
    color: str
    rent_multiplier: float | None


class BoardTileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    position: int
    name: str
    kind: str
    group_id: str | None
    price: int | None
    rent_model: str
    rent_table: list[int]
    upgrade_costs: list[int]
    mortgage_value: int | None
    tax_config: dict[str, Any]
    mystery_deck_key: str
    special_effects: list[Any]


class BoardSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    name: str
    description: str
    size: int
    is_preset: bool
    owner_user_id: str | None


class BoardDetailOut(BoardSummaryOut):
    groups: list[BoardGroupOut]
    tiles: list[BoardTileOut]


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    from_player_id: str | None
    to_player_id: str | None
    amount: int
    reason: str
    created_by_player_id: str | None
    reversed: bool
    status: str
    created_at: datetime


class EventLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    player_ids: list[str]
    payload: dict[str, Any]
    created_at: datetime


class GameStateOut(BaseModel):
    id: str
    code: str
    name: str
    status: str
    money_mode: str
    banker_mode: str
    play_mode: str
    board: BoardDetailOut
    ruleset: dict[str, Any]
    inflation_multiplier: float
    round_number: int
    free_parking_pot_amount: int
    turn_order: list[str]
    current_turn_player_id: str | None
    pending_turn_order_rolls: list[dict[str, Any]]
    players: list[PlayerOut]
    properties: list[PropertyOut]
    recent_log: list[EventLogOut]
    pending_transfers: list[TransactionOut]


class GameCreateResponse(BaseModel):
    game: GameStateOut
    host_player_id: str
    host_token: str
    player_token: str


class JoinGameResponse(BaseModel):
    game: GameStateOut
    player_id: str
    player_token: str


class ManualTransactionRequest(BaseModel):
    from_player_id: str | None = None
    to_player_id: str | None = None
    amount: int = Field(ge=0)
    reason: str = Field(default="", max_length=120)


class LandRequest(BaseModel):
    player_id: str
    space_index: int = Field(ge=0)
    dice_roll: int | None = Field(default=None, ge=2, le=12)


class PromoteBankerRequest(BaseModel):
    player_id: str
    is_banker: bool = True


class TransferRequest(BaseModel):
    other_player_id: str
    amount: int = Field(ge=1)
    reason: str = Field(default="", max_length=120)


class DrawEventRequest(BaseModel):
    player_id: str
    space_index: int = Field(ge=0)


class RollRequest(BaseModel):
    use_jail_free_card: bool = False
    pay_fine: bool = False


class AddBotRequest(BaseModel):
    name: str | None = Field(default=None, max_length=40)


class RollForOrderRequest(BaseModel):
    player_id: str
    roll: int = Field(ge=1)


class RollForPlayerRequest(BaseModel):
    player_id: str
    dice: list[int] = Field(min_length=1, max_length=4)
    use_jail_free_card: bool = False
    pay_fine: bool = False


class MovePlayerRequest(BaseModel):
    player_id: str
    position: int = Field(ge=0)
    resolve_landing: bool = True


class SwapPlayersRequest(BaseModel):
    player_a_id: str
    player_b_id: str


class SaveBoardTemplateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=200)
