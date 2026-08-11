import mongoose from "mongoose";

const CATEGORIES = [
  "purchase",
  "rent",
  "tax",
  "salary",
  "mortgage",
  "unmortgage",
  "house",
  "sell_house",
  "loan",
  "loan_repayment",
  "fine",
  "other",
];

const transactionSchema = new mongoose.Schema(
  {
    game: { type: mongoose.Schema.Types.ObjectId, ref: "Game", required: true },
    fromType: { type: String, enum: ["player", "bank"], required: true },
    fromPlayer: { type: mongoose.Schema.Types.ObjectId, default: null },
    toType: { type: String, enum: ["player", "bank"], required: true },
    toPlayer: { type: mongoose.Schema.Types.ObjectId, default: null },
    amount: { type: Number, required: true },
    category: { type: String, enum: CATEGORIES, default: "other" },
    note: { type: String, default: "" },
    position: { type: Number, default: null },
  },
  { timestamps: true }
);

export const TRANSACTION_CATEGORIES = CATEGORIES;
export default mongoose.model("Transaction", transactionSchema);
