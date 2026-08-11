import mongoose from "mongoose";

const debtSchema = new mongoose.Schema(
  {
    game: { type: mongoose.Schema.Types.ObjectId, ref: "Game", required: true },
    fromPlayer: { type: mongoose.Schema.Types.ObjectId, required: true },
    toPlayer: { type: mongoose.Schema.Types.ObjectId, required: true },
    amount: { type: Number, required: true },
    reason: { type: String, default: "" },
    settled: { type: Boolean, default: false },
    settledAt: { type: Date, default: null },
  },
  { timestamps: true }
);

export default mongoose.model("Debt", debtSchema);
