from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GameCreateRequest(BaseModel):
    host_name: str = Field(min_length=1, max_length=40)
    name: str = Field(default="Monopoly Night", max_length=60)
    starting_cash: int | None = Field(default=None, ge=0)
    banker_mode: Literal["manual", "auto"] = "manual"


class JoinGameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    is_host: bool
    is_banker: bool
    balance: int
    status: str


class PropertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    space_index: int
    name: str
    owner_id: str | None
    price: int
    houses: int
    mortgaged: bool


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
    ruleset: dict[str, Any]
    players: list[PlayerOut]
    properties: list[PropertyOut]
    recent_log: list[EventLogOut]


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
    space_index: int = Field(ge=0, le=39)
    dice_roll: int | None = Field(default=None, ge=2, le=12)


class PromoteBankerRequest(BaseModel):
    player_id: str
    is_banker: bool = True
