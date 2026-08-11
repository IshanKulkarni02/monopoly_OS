import mongoose from "mongoose";
import { VARIANT_KEYS } from "../data/variants.js";

const playerSchema = new mongoose.Schema({
  name: { type: String, required: true },
  color: { type: String, default: "#c0142c" },
  startingCash: { type: Number, required: true },
  cash: { type: Number, required: true },
  position: { type: Number, default: 0 },
  inJail: { type: Boolean, default: false },
});

const propertySchema = new mongoose.Schema({
  position: { type: Number, required: true },
  name: { type: String, required: true },
  type: { type: String, required: true },
  color: { type: String, default: null },
  price: { type: Number, default: null },
  mortgageValue: { type: Number, default: null },
  houseCost: { type: Number, default: null },
  rent: { type: [Number], default: [] },
  ownerId: { type: mongoose.Schema.Types.ObjectId, default: null },
  mortgaged: { type: Boolean, default: false },
  // 0-4 = houses, 5 = hotel. Only meaningful for type "property".
  houses: { type: Number, default: 0 },
});

const rulesSchema = new mongoose.Schema(
  {
    goBonus: { type: Number, default: 200 },
    freeParkingJackpot: { type: Boolean, default: false },
    jailRentSuspended: { type: Boolean, default: false },
    buildingLimits: { type: String, enum: ["standard", "infinite"], default: "standard" },
  },
  { _id: false }
);

const gameSchema = new mongoose.Schema(
  {
    name: { type: String, required: true },
    variant: { type: String, enum: VARIANT_KEYS, default: "classic" },
    boardKey: { type: String, required: true, default: "classic" },
    boardSize: { type: Number, required: true },
    players: [playerSchema],
    properties: [propertySchema],
    status: { type: String, enum: ["active", "ended"], default: "active" },
    diceMode: { type: String, enum: ["single", "double"], default: "double" },
    rules: { type: rulesSchema, default: () => ({}) },
    freeParkingPot: { type: Number, default: 0 },
    // Physical building supply, per the real 32-house/12-hotel bank limit.
    // Only enforced when rules.buildingLimits === "standard".
    bankHouses: { type: Number, default: 32 },
    bankHotels: { type: Number, default: 12 },
    // Filled in as each player takes their first move, in the real-world
    // order the host records them — this *is* the turn order, not a
    // pre-assignment. Once it holds every player, turns lock into
    // round-robin and currentPlayerId auto-advances.
    turnOrder: { type: [mongoose.Schema.Types.ObjectId], default: [] },
    currentPlayerId: { type: mongoose.Schema.Types.ObjectId, default: null },
  },
  { timestamps: true }
);

export default mongoose.model("Game", gameSchema);
