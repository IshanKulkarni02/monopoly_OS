import "dotenv/config";
import cors from "cors";
import express from "express";
import { connectDB } from "./config/db.js";
import healthRouter from "./routes/health.js";
import tilesRouter from "./routes/tiles.js";
import gamesRouter from "./routes/games.js";
import Tile from "./models/Tile.js";
import { classicBoard } from "./data/classicBoard.js";
import { megaBoard } from "./data/megaBoard.js";

const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/monopoly_manager";

const app = express();
app.use(cors());
app.use(express.json());

app.use("/api/health", healthRouter);
app.use("/api/tiles", tilesRouter);
app.use("/api/games", gamesRouter);

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: err.message || "Internal server error" });
});

async function seedBoard(boardKey, tiles) {
  const count = await Tile.countDocuments({ boardKey });
  if (count === 0) {
    await Tile.insertMany(tiles.map((t) => ({ ...t, boardKey })));
    console.log(`Seeded ${boardKey} board (${tiles.length} tiles)`);
  }
}

async function start() {
  await connectDB(MONGODB_URI);
  // Drops the old single-field unique index on `position` (pre-dates
  // multi-board support) and creates the current (boardKey, position) one.
  await Tile.syncIndexes();
  await seedBoard("classic", classicBoard);
  await seedBoard("mega", megaBoard);
  app.listen(PORT, () => {
    console.log(`API listening on http://localhost:${PORT}`);
  });
}

start().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});
