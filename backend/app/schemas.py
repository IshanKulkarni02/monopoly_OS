from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _ensure_utc(value: datetime | None) -> datetime | None:
    """SQLite has no real timezone-aware storage type, so SQLAlchemy's
    `DateTime(timezone=True)` columns round-trip as naive datetimes even
    though every write uses `datetime.now(timezone.utc)` — the tzinfo is
    silently dropped on read-back. Serializing that naive value straight to
    JSON omits the UTC offset, and a browser's `new Date(...)` treats an
    offset-less ISO string as *local* time, not UTC — in any timezone ahead
    of UTC this makes a just-set timestamp parse as being in the future (or,
    for a deadline computed from it, already in the past). Every datetime
    field exposed via the API routes through this so the wire format always
    carries an explicit UTC offset, regardless of what SQLite handed back."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


UtcDatetime = Annotated[datetime, BeforeValidator(_ensure_utc)]


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
    mystery_deck_mode: Literal["probability", "finite"] = "probability"
    track_denominations: bool = False
    auction_enabled: bool = False
    trading_enabled: bool = True
    turn_timer_seconds: int = Field(default=0, ge=0, le=3600)


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
    net_worth: int = 0


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
    locked: bool


class BoardSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    key: str
    name: str
    description: str
    size: int
    is_preset: bool
    owner_user_id: str | None
    default_ruleset_overrides: dict[str, Any] = {}
    preset_play_options: dict[str, Any] = {}


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
    created_at: UtcDatetime


class EventLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    player_ids: list[str]
    payload: dict[str, Any]
    created_at: UtcDatetime


class AuctionOut(BaseModel):
    property_id: str
    property_name: str
    current_bid: int
    current_bidder_id: str | None
    eligible_ids: list[str]
    passed_ids: list[str]
    started_by: str


class StartAuctionRequest(BaseModel):
    property_id: str


class BidRequest(BaseModel):
    amount: int = Field(ge=1)


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    proposer_id: str
    recipient_id: str
    offer_cash: int
    offer_property_ids: list[str]
    offer_jail_cards: int
    request_cash: int
    request_property_ids: list[str]
    request_jail_cards: int
    status: str
    created_at: UtcDatetime


class ProposeTradeRequest(BaseModel):
    recipient_id: str
    offer_cash: int = Field(default=0, ge=0)
    offer_property_ids: list[str] = []
    offer_jail_cards: int = Field(default=0, ge=0)
    request_cash: int = Field(default=0, ge=0)
    request_property_ids: list[str] = []
    request_jail_cards: int = Field(default=0, ge=0)


class DeclareBankruptcyRequest(BaseModel):
    creditor_player_id: str | None = None


class ImportGameRequest(BaseModel):
    data: dict[str, Any]


class SimulateRequest(BaseModel):
    board_key: str
    ruleset_overrides: dict[str, Any] = {}
    num_games: int = Field(default=10, ge=1, le=50)
    num_bots: int = Field(default=4, ge=2, le=6)
    max_turns: int = Field(default=500, ge=50, le=1000)


class CompareSimulationRequest(BaseModel):
    board_key: str
    baseline_overrides: dict[str, Any] = {}
    variant_overrides: dict[str, Any] = {}
    num_games: int = Field(default=10, ge=1, le=50)
    num_bots: int = Field(default=4, ge=2, le=6)
    max_turns: int = Field(default=500, ge=50, le=1000)


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
    turn_started_at: UtcDatetime | None = None
    winner_player_id: str | None = None
    pending_turn_order_rolls: list[dict[str, Any]]
    players: list[PlayerOut]
    properties: list[PropertyOut]
    recent_log: list[EventLogOut]
    pending_transfers: list[TransactionOut]
    active_auction: dict[str, Any] = {}
    pending_trades: list[TradeOut] = []


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


class DuplicateBoardRequest(BaseModel):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=60)
    description: str = Field(default="", max_length=200)


class UpdateBoardRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = Field(default=None, max_length=200)


class TileFieldsRequest(BaseModel):
    """Shared by insert/update — every field optional so PATCH-style partial
    updates work, and so insert can omit anything not relevant to a kind
    (e.g. a 'go' tile has no price)."""
    name: str | None = None
    kind: str | None = None
    group_id: str | None = None
    price: int | None = Field(default=None, ge=0)
    rent_model: str | None = None
    rent_table: list[int] | None = None
    upgrade_costs: list[int] | None = None
    mortgage_value: int | None = Field(default=None, ge=0)
    tax_config: dict[str, Any] | None = None
    mystery_deck_key: str | None = None
    special_effects: list[Any] | None = None
    locked: bool | None = None


class InsertTileRequest(BaseModel):
    position: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=60)
    kind: str
    fields: TileFieldsRequest = TileFieldsRequest()


class MoveTileRequest(BaseModel):
    other_tile_id: str


class CreateGroupRequest(BaseModel):
    key: str = Field(min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=40)
    color: str = Field(default="#888888", max_length=20)
    rent_multiplier: float | None = Field(default=None, ge=0)


class UpdateGroupRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, max_length=20)
    rent_multiplier: float | None = None


class RegenerateLayoutRequest(BaseModel):
    group_constraints: dict[str, dict[str, int | None]] = {}
    seed: int | None = None


MYSTERY_EFFECT_KINDS = [
    "bank_pays", "pay_bank", "pay_each_player", "collect_each_player", "jail_free",
    "pass_go", "move_forward", "move_backward", "move_to", "lose_turn", "extra_turn", "nothing",
]


class MysteryCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    deck_key: str
    text: str
    effect_kind: str
    amount: int
    target_position: int | None
    weight: int


class CreateMysteryCardRequest(BaseModel):
    deck_key: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=200)
    effect_kind: Literal[
        "bank_pays", "pay_bank", "pay_each_player", "collect_each_player", "jail_free",
        "pass_go", "move_forward", "move_backward", "move_to", "lose_turn", "extra_turn", "nothing",
    ]
    amount: int = Field(default=0, ge=0)
    target_position: int | None = Field(default=None, ge=0)
    weight: int = Field(default=1, ge=1)


class UpdateMysteryCardRequest(BaseModel):
    deck_key: str | None = Field(default=None, min_length=1, max_length=40)
    text: str | None = Field(default=None, min_length=1, max_length=200)
    effect_kind: str | None = None
    amount: int | None = Field(default=None, ge=0)
    target_position: int | None = Field(default=None, ge=0)
    weight: int | None = Field(default=None, ge=1)


class MakeChangeRequest(BaseModel):
    amount: int = Field(ge=0)
    denominations: list[int] = Field(min_length=1)


class MakeChangeResponse(BaseModel):
    breakdown: dict[str, int]
