import { Router } from "express";
import Tile from "../models/Tile.js";
import { asyncHandler } from "../utils/asyncHandler.js";

const router = Router();

function boardKeyOf(req) {
  return req.query.board || "classic";
}

router.get(
  "/boards",
  asyncHandler(async (req, res) => {
    const keys = await Tile.distinct("boardKey");
    res.json(keys);
  })
);

router.get(
  "/",
  asyncHandler(async (req, res) => {
    const tiles = await Tile.find({ boardKey: boardKeyOf(req) }).sort({ position: 1 });
    res.json(tiles);
  })
);

router.post(
  "/",
  asyncHandler(async (req, res) => {
    const boardKey = boardKeyOf(req);
    const count = await Tile.countDocuments({ boardKey });
    const tile = await Tile.create({ ...req.body, boardKey, position: count });
    res.status(201).json(tile);
  })
);

router.put(
  "/:id",
  asyncHandler(async (req, res) => {
    const { position, boardKey, ...updates } = req.body;
    const tile = await Tile.findByIdAndUpdate(req.params.id, updates, {
      new: true,
      runValidators: true,
    });
    if (!tile) return res.status(404).json({ error: "Tile not found" });
    res.json(tile);
  })
);

router.put(
  "/:id/move",
  asyncHandler(async (req, res) => {
    const { direction } = req.body;
    const tile = await Tile.findById(req.params.id);
    if (!tile) return res.status(404).json({ error: "Tile not found" });

    const targetPosition = tile.position + (direction === "up" ? -1 : 1);
    const neighbor = await Tile.findOne({
      boardKey: tile.boardKey,
      position: targetPosition,
    });
    if (!neighbor) return res.json(tile);

    const originalPosition = tile.position;

    // The unique index on (boardKey, position) rejects a save that collides
    // with a still-persisted value, so stage the moving tile at a scratch
    // position before the neighbor takes its old slot.
    tile.position = -1;
    await tile.save();

    neighbor.position = originalPosition;
    await neighbor.save();

    tile.position = targetPosition;
    await tile.save();

    const tiles = await Tile.find({ boardKey: tile.boardKey }).sort({ position: 1 });
    res.json(tiles);
  })
);

router.delete(
  "/:id",
  asyncHandler(async (req, res) => {
    const tile = await Tile.findByIdAndDelete(req.params.id);
    if (!tile) return res.status(404).json({ error: "Tile not found" });

    await Tile.updateMany(
      { boardKey: tile.boardKey, position: { $gt: tile.position } },
      { $inc: { position: -1 } }
    );

    const tiles = await Tile.find({ boardKey: tile.boardKey }).sort({ position: 1 });
    res.json(tiles);
  })
);

export default router;
