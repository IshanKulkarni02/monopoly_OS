"""Stateless currency utilities — the change-making calculator (spec §7).
No game/auth context needed; it's pure math over whatever denominations the
caller passes in."""

from fastapi import APIRouter, HTTPException

from app import schemas
from app.game_engine import currency as currency_engine

router = APIRouter(prefix="/api/currency", tags=["currency"])


@router.post("/make_change", response_model=schemas.MakeChangeResponse)
def make_change(payload: schemas.MakeChangeRequest):
    try:
        breakdown = currency_engine.make_change(payload.amount, payload.denominations)
    except currency_engine.CurrencyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.MakeChangeResponse(breakdown={str(k): v for k, v in breakdown.items()})
