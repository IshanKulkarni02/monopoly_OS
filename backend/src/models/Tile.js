import mongoose from "mongoose";

const TILE_TYPES = [
  "go",
  "property",
  "railroad",
  "utility",
  "chance",
  "community_chest",
  "tax",
  "jail",
  "free_parking",
  "go_to_jail",
];

const tileSchema = new mongoose.Schema(
  {
    boardKey: { type: String, required: true, default: "classic" },
    position: { type: Number, required: true },
    name: { type: String, required: true },
    type: { type: String, enum: TILE_TYPES, required: true },
    color: { type: String, default: null },
    price: { type: Number, default: null },
    rent: { type: [Number], default: [] },
    houseCost: { type: Number, default: null },
    mortgageValue: { type: Number, default: null },
    taxAmount: { type: Number, default: null },
  },
  { timestamps: true }
);

tileSchema.index({ boardKey: 1, position: 1 }, { unique: true });

export const TILE_TYPE_VALUES = TILE_TYPES;
export default mongoose.model("Tile", tileSchema);
