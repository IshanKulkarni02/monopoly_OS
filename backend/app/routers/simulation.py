from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.game_engine import board_engine, probability, simulation

router = APIRouter(prefix="/api", tags=["simulation"])


@router.post("/simulate")
def simulate(payload: schemas.SimulateRequest, db: Session = Depends(get_db)):
    try:
        return simulation.simulate_batch(
            db,
            board_key=payload.board_key,
            ruleset_overrides=payload.ruleset_overrides or None,
            num_games=payload.num_games,
            num_bots=payload.num_bots,
            max_turns=payload.max_turns,
        )
    except (simulation.SimulationError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/simulate/compare")
def simulate_compare(payload: schemas.CompareSimulationRequest, db: Session = Depends(get_db)):
    try:
        baseline = simulation.simulate_batch(
            db, board_key=payload.board_key, ruleset_overrides=payload.baseline_overrides or None,
            num_games=payload.num_games, num_bots=payload.num_bots, max_turns=payload.max_turns,
        )
        variant = simulation.simulate_batch(
            db, board_key=payload.board_key, ruleset_overrides=payload.variant_overrides or None,
            num_games=payload.num_games, num_bots=payload.num_bots, max_turns=payload.max_turns,
        )
    except (simulation.SimulationError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"baseline": baseline, "variant": variant}


@router.get("/boards/{key}/landing_probabilities")
def landing_probabilities(key: str, db: Session = Depends(get_db), dice_count: int = Query(default=2, ge=1, le=4)):
    board = board_engine.get_board_by_key(db, key)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    try:
        return {"tiles": probability.compute_landing_probabilities(db, board, dice_count=dice_count)}
    except probability.ProbabilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
