import { Router } from "express";
import Game from "../models/Game.js";
import Transaction from "../models/Transaction.js";
import Debt from "../models/Debt.js";
import Tile from "../models/Tile.js";
import { asyncHandler } from "../utils/asyncHandler.js";
import { computeRent } from "../utils/rent.js";
import { VARIANTS } from "../data/variants.js";

const router = Router();
const OWNABLE_TYPES = ["property", "railroad", "utility"];

const loadGame = asyncHandler(async (req, res, next) => {
  const game = await Game.findById(req.params.id);
  if (!game) return res.status(404).json({ error: "Game not found" });
  req.game = game;
  next();
});

function findPlayer(game, playerId) {
  return game.players.id(playerId);
}

function applyLedgerEntry(game, { fromType, fromPlayer, toType, toPlayer, amount }) {
  if (fromType === "player") {
    const p = findPlayer(game, fromPlayer);
    if (!p) throw new Error("fromPlayer not found");
    p.cash -= amount;
  }
  if (toType === "player") {
    const p = findPlayer(game, toPlayer);
    if (!p) throw new Error("toPlayer not found");
    p.cash += amount;
  }
}

// ---- Games ----

router.get(
  "/variants",
  asyncHandler(async (req, res) => {
    res.json(
      Object.entries(VARIANTS).map(([key, v]) => ({
        key,
        label: v.label,
        description: v.description,
        implemented: v.implemented,
      }))
    );
  })
);

router.get(
  "/",
  asyncHandler(async (req, res) => {
    const games = await Game.find()
      .select("name status players createdAt")
      .sort({ createdAt: -1 });
    res.json(
      games.map((g) => ({
        _id: g._id,
        name: g.name,
        status: g.status,
        playerCount: g.players.length,
        createdAt: g.createdAt,
      }))
    );
  })
);

router.post(
  "/",
  asyncHandler(async (req, res) => {
    const { name, players, diceMode, variant, rules } = req.body;
    if (!name || !Array.isArray(players) || players.length === 0) {
      return res.status(400).json({ error: "name and at least one player are required" });
    }

    const variantKey = variant && VARIANTS[variant] ? variant : "classic";
    const variantDef = VARIANTS[variantKey];
    if (!variantDef.implemented) {
      return res.status(400).json({
        error: `${variantDef.label} isn't implemented yet — pick Classic or Mega Edition.`,
      });
    }

    const tiles = await Tile.find({ boardKey: variantDef.boardKey }).sort({ position: 1 });
    if (tiles.length === 0) {
      return res.status(400).json({ error: "Board has no tiles yet" });
    }

    const properties = tiles
      .filter((t) => OWNABLE_TYPES.includes(t.type))
      .map((t) => ({
        position: t.position,
        name: t.name,
        type: t.type,
        color: t.color,
        price: t.price,
        mortgageValue: t.mortgageValue,
        houseCost: t.houseCost,
        rent: t.rent,
        ownerId: null,
        mortgaged: false,
        houses: 0,
      }));

    const game = await Game.create({
      name,
      variant: variantKey,
      boardKey: variantDef.boardKey,
      boardSize: tiles.length,
      diceMode: diceMode === "single" ? "single" : "double",
      rules: {
        goBonus: rules?.goBonus === 400 ? 400 : 200,
        freeParkingJackpot: !!rules?.freeParkingJackpot,
        jailRentSuspended: !!rules?.jailRentSuspended,
        buildingLimits: rules?.buildingLimits === "infinite" ? "infinite" : "standard",
      },
      players: players.map((p) => ({
        name: p.name,
        color: p.color || "#c0142c",
        startingCash: p.startingCash,
        cash: p.startingCash,
        position: 0,
      })),
      properties,
    });

    res.status(201).json(game);
  })
);

router.get(
  "/:id",
  loadGame,
  asyncHandler(async (req, res) => {
    res.json(req.game);
  })
);

router.delete(
  "/:id",
  loadGame,
  asyncHandler(async (req, res) => {
    await req.game.deleteOne();
    await Transaction.deleteMany({ game: req.game._id });
    await Debt.deleteMany({ game: req.game._id });
    res.status(204).end();
  })
);

router.put(
  "/:id/dice-mode",
  loadGame,
  asyncHandler(async (req, res) => {
    const { diceMode } = req.body;
    if (!["single", "double"].includes(diceMode)) {
      return res.status(400).json({ error: "diceMode must be 'single' or 'double'" });
    }
    req.game.diceMode = diceMode;
    await req.game.save();
    res.json(req.game);
  })
);

// ---- Players ----

router.post(
  "/:id/players",
  loadGame,
  asyncHandler(async (req, res) => {
    const { name, color, startingCash } = req.body;
    if (!name || startingCash == null) {
      return res.status(400).json({ error: "name and startingCash are required" });
    }
    req.game.players.push({
      name,
      color: color || "#c0142c",
      startingCash,
      cash: startingCash,
      position: 0,
    });
    // A new player hasn't moved yet, so turn order is no longer complete —
    // back to flexible selection until they (and everyone) has a first move.
    req.game.currentPlayerId = null;
    await req.game.save();
    res.status(201).json(req.game);
  })
);

router.put(
  "/:id/players/:playerId/move",
  loadGame,
  asyncHandler(async (req, res) => {
    const { steps } = req.body;
    const player = findPlayer(req.game, req.params.playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });
    if (typeof steps !== "number") {
      return res.status(400).json({ error: "steps must be a number" });
    }

    const boardSize = req.game.boardSize;
    const before = player.position;
    const raw = before + steps;
    const passedGo = steps > 0 && raw >= boardSize;
    player.position = ((raw % boardSize) + boardSize) % boardSize;

    // Turn order isn't pre-assigned: whichever player the host records a
    // move for first becomes P1, the next new player becomes P2, etc. The
    // mover becomes (or stays) the current player — advancing to the next
    // player only happens via an explicit End Turn, once they've resolved
    // whatever landing here requires (buy, pay rent, ...).
    const alreadyInOrder = req.game.turnOrder.some(
      (id) => String(id) === String(player._id)
    );
    if (!alreadyInOrder) {
      req.game.turnOrder.push(player._id);
    }
    req.game.currentPlayerId = player._id;

    const landedProperty = req.game.properties.find(
      (p) => p.position === player.position
    );
    let rentDue = null;
    if (landedProperty && String(landedProperty.ownerId) !== String(player._id)) {
      const amount = computeRent(req.game, landedProperty, steps);
      if (amount > 0) {
        rentDue = {
          position: landedProperty.position,
          name: landedProperty.name,
          ownerId: landedProperty.ownerId,
          amount,
        };
      }
    }

    await req.game.save();
    res.json({ game: req.game, passedGo, rentDue });
  })
);

router.put(
  "/:id/players/:playerId/end-turn",
  loadGame,
  asyncHandler(async (req, res) => {
    const player = findPlayer(req.game, req.params.playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });
    if (req.game.turnOrder.length !== req.game.players.length) {
      return res.status(400).json({ error: "Turn order isn't locked in yet" });
    }
    if (String(req.game.currentPlayerId) !== String(player._id)) {
      return res.status(400).json({ error: "It isn't this player's turn" });
    }
    const idx = req.game.turnOrder.findIndex(
      (id) => String(id) === String(player._id)
    );
    const nextIdx = (idx + 1) % req.game.turnOrder.length;
    req.game.currentPlayerId = req.game.turnOrder[nextIdx];
    await req.game.save();
    res.json(req.game);
  })
);

router.put(
  "/:id/players/:playerId/position",
  loadGame,
  asyncHandler(async (req, res) => {
    const { position } = req.body;
    const player = findPlayer(req.game, req.params.playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });
    if (typeof position !== "number" || position < 0 || position >= req.game.boardSize) {
      return res.status(400).json({ error: "invalid position" });
    }
    player.position = position;
    await req.game.save();
    res.json(req.game);
  })
);

router.put(
  "/:id/players/:playerId/jail",
  loadGame,
  asyncHandler(async (req, res) => {
    const { inJail } = req.body;
    const player = findPlayer(req.game, req.params.playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });
    player.inJail = !!inJail;
    await req.game.save();
    res.json(req.game);
  })
);

// ---- Transactions ----

router.get(
  "/:id/transactions",
  loadGame,
  asyncHandler(async (req, res) => {
    const transactions = await Transaction.find({ game: req.game._id }).sort({ createdAt: -1 });
    res.json(transactions);
  })
);

router.post(
  "/:id/transactions",
  loadGame,
  asyncHandler(async (req, res) => {
    const { fromType, fromPlayer, toType, toPlayer, amount, category, note, position } = req.body;

    if (!["player", "bank"].includes(fromType) || !["player", "bank"].includes(toType)) {
      return res.status(400).json({ error: "fromType/toType must be 'player' or 'bank'" });
    }
    if (typeof amount !== "number" || amount <= 0) {
      return res.status(400).json({ error: "amount must be a positive number" });
    }
    if (fromType === "bank" && toType === "bank") {
      return res.status(400).json({ error: "at least one side must be a player" });
    }

    try {
      applyLedgerEntry(req.game, { fromType, fromPlayer, toType, toPlayer, amount });
    } catch (err) {
      return res.status(404).json({ error: err.message });
    }

    if (
      req.game.rules.freeParkingJackpot &&
      toType === "bank" &&
      ["tax", "fine"].includes(category)
    ) {
      req.game.freeParkingPot += amount;
    }

    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType,
      fromPlayer: fromType === "player" ? fromPlayer : null,
      toType,
      toPlayer: toType === "player" ? toPlayer : null,
      amount,
      category: category || "other",
      note: note || "",
      position: position ?? null,
    });

    res.status(201).json({ game: req.game, transaction });
  })
);

router.post(
  "/:id/free-parking/claim",
  loadGame,
  asyncHandler(async (req, res) => {
    const { playerId } = req.body;
    const player = findPlayer(req.game, playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });
    if (req.game.freeParkingPot <= 0) {
      return res.status(400).json({ error: "Free Parking pot is empty" });
    }

    const amount = req.game.freeParkingPot;
    player.cash += amount;
    req.game.freeParkingPot = 0;
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "bank",
      toType: "player",
      toPlayer: player._id,
      amount,
      category: "other",
      note: "Free Parking jackpot",
    });

    res.json({ game: req.game, transaction });
  })
);

// ---- Properties ----

function findProperty(game, position) {
  return game.properties.find((p) => p.position === Number(position));
}

router.post(
  "/:id/properties/:position/buy",
  loadGame,
  asyncHandler(async (req, res) => {
    const { playerId } = req.body;
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (property.ownerId) return res.status(400).json({ error: "Property already owned" });

    const player = findPlayer(req.game, playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });

    const price = property.price || 0;
    property.ownerId = player._id;
    player.cash -= price;
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "player",
      fromPlayer: player._id,
      toType: "bank",
      toPlayer: null,
      amount: price,
      category: "purchase",
      note: property.name,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

router.post(
  "/:id/properties/:position/auction",
  loadGame,
  asyncHandler(async (req, res) => {
    const { playerId, amount } = req.body;
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (property.ownerId) return res.status(400).json({ error: "Property already owned" });
    if (typeof amount !== "number" || amount <= 0) {
      return res.status(400).json({ error: "Winning bid must be a positive number" });
    }

    const player = findPlayer(req.game, playerId);
    if (!player) return res.status(404).json({ error: "Player not found" });

    property.ownerId = player._id;
    player.cash -= amount;
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "player",
      fromPlayer: player._id,
      toType: "bank",
      amount,
      category: "purchase",
      note: `${property.name} (auction)`,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

router.post(
  "/:id/properties/:position/mortgage",
  loadGame,
  asyncHandler(async (req, res) => {
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (!property.ownerId) return res.status(400).json({ error: "Property is not owned" });
    if (property.mortgaged) return res.status(400).json({ error: "Already mortgaged" });
    if (property.houses > 0) {
      return res.status(400).json({ error: "Sell the houses/hotel before mortgaging" });
    }

    const player = findPlayer(req.game, property.ownerId);
    const value = property.mortgageValue || 0;
    property.mortgaged = true;
    player.cash += value;
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "bank",
      toType: "player",
      toPlayer: player._id,
      amount: value,
      category: "mortgage",
      note: property.name,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

router.post(
  "/:id/properties/:position/unmortgage",
  loadGame,
  asyncHandler(async (req, res) => {
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (!property.mortgaged) return res.status(400).json({ error: "Not mortgaged" });

    const player = findPlayer(req.game, property.ownerId);
    const value = Math.round((property.mortgageValue || 0) * 1.1);
    property.mortgaged = false;
    player.cash -= value;
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "player",
      fromPlayer: player._id,
      toType: "bank",
      amount: value,
      category: "unmortgage",
      note: property.name,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

function propertyGroup(game, property) {
  return game.properties.filter(
    (p) => p.type === "property" && p.color === property.color
  );
}

router.post(
  "/:id/properties/:position/build-house",
  loadGame,
  asyncHandler(async (req, res) => {
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (property.type !== "property") {
      return res.status(400).json({ error: "Only color-group properties can have houses" });
    }
    if (!property.ownerId) return res.status(400).json({ error: "Property is not owned" });
    if (property.mortgaged) return res.status(400).json({ error: "Property is mortgaged" });
    if (property.houses >= 5) {
      return res.status(400).json({ error: "Already has a hotel" });
    }

    const group = propertyGroup(req.game, property);
    if (!group.every((p) => String(p.ownerId) === String(property.ownerId))) {
      return res.status(400).json({ error: "Owner doesn't hold the full color group" });
    }
    if (group.some((p) => p.mortgaged)) {
      return res.status(400).json({ error: "A property in this group is mortgaged" });
    }
    const minHouses = Math.min(...group.map((p) => p.houses));
    if (property.houses > minHouses) {
      return res.status(400).json({
        error: "Build evenly — build on the least-developed property in the group first",
      });
    }

    const buildingHotel = property.houses === 4;
    if (req.game.rules.buildingLimits === "standard") {
      if (buildingHotel && req.game.bankHotels <= 0) {
        return res.status(400).json({ error: "The bank is out of hotels" });
      }
      if (!buildingHotel && req.game.bankHouses <= 0) {
        return res.status(400).json({ error: "The bank is out of houses" });
      }
    }

    const player = findPlayer(req.game, property.ownerId);
    const cost = property.houseCost || 0;
    property.houses += 1;
    player.cash -= cost;
    if (buildingHotel) {
      req.game.bankHotels -= 1;
      req.game.bankHouses += 4; // the 4 houses return to the bank's supply
    } else {
      req.game.bankHouses -= 1;
    }
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "player",
      fromPlayer: player._id,
      toType: "bank",
      amount: cost,
      category: "house",
      note: `${property.name} (${property.houses === 5 ? "hotel" : `house ${property.houses}`})`,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

router.post(
  "/:id/properties/:position/sell-house",
  loadGame,
  asyncHandler(async (req, res) => {
    const property = findProperty(req.game, req.params.position);
    if (!property) return res.status(404).json({ error: "Property not found" });
    if (property.houses <= 0) {
      return res.status(400).json({ error: "No houses to sell" });
    }

    const group = propertyGroup(req.game, property);
    const maxHouses = Math.max(...group.map((p) => p.houses));
    if (property.houses < maxHouses) {
      return res.status(400).json({
        error: "Sell evenly — sell from the most-developed property in the group first",
      });
    }

    const wasHotel = property.houses === 5;
    if (
      req.game.rules.buildingLimits === "standard" &&
      wasHotel &&
      req.game.bankHouses < 4
    ) {
      return res.status(400).json({
        error: "Not enough houses in the bank to convert the hotel back",
      });
    }

    const player = findPlayer(req.game, property.ownerId);
    const refund = Math.round((property.houseCost || 0) / 2);
    property.houses -= 1;
    player.cash += refund;
    if (wasHotel) {
      req.game.bankHotels += 1;
      req.game.bankHouses -= 4;
    } else {
      req.game.bankHouses += 1;
    }
    await req.game.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "bank",
      toType: "player",
      toPlayer: player._id,
      amount: refund,
      category: "sell_house",
      note: `${property.name} (sold ${wasHotel ? "hotel" : "house"})`,
      position: property.position,
    });

    res.json({ game: req.game, transaction });
  })
);

// ---- Debts ----

router.get(
  "/:id/debts",
  loadGame,
  asyncHandler(async (req, res) => {
    const debts = await Debt.find({ game: req.game._id }).sort({ createdAt: -1 });
    res.json(debts);
  })
);

router.post(
  "/:id/debts",
  loadGame,
  asyncHandler(async (req, res) => {
    const { fromPlayer, toPlayer, amount, reason } = req.body;
    if (!findPlayer(req.game, fromPlayer) || !findPlayer(req.game, toPlayer)) {
      return res.status(404).json({ error: "Player not found" });
    }
    if (typeof amount !== "number" || amount <= 0) {
      return res.status(400).json({ error: "amount must be a positive number" });
    }
    const debt = await Debt.create({
      game: req.game._id,
      fromPlayer,
      toPlayer,
      amount,
      reason: reason || "",
    });
    res.status(201).json(debt);
  })
);

router.post(
  "/:id/debts/:debtId/settle",
  loadGame,
  asyncHandler(async (req, res) => {
    const debt = await Debt.findOne({ _id: req.params.debtId, game: req.game._id });
    if (!debt) return res.status(404).json({ error: "Debt not found" });
    if (debt.settled) return res.status(400).json({ error: "Already settled" });

    applyLedgerEntry(req.game, {
      fromType: "player",
      fromPlayer: debt.fromPlayer,
      toType: "player",
      toPlayer: debt.toPlayer,
      amount: debt.amount,
    });
    await req.game.save();

    debt.settled = true;
    debt.settledAt = new Date();
    await debt.save();

    const transaction = await Transaction.create({
      game: req.game._id,
      fromType: "player",
      fromPlayer: debt.fromPlayer,
      toType: "player",
      toPlayer: debt.toPlayer,
      amount: debt.amount,
      category: "loan_repayment",
      note: debt.reason,
    });

    res.json({ game: req.game, debt, transaction });
  })
);

export default router;
