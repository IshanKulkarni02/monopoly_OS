# Monopoly Manager

MERN stack app: MongoDB, Express, React (Vite), Node.

## Structure

- `backend/` — Express API + Mongoose models, connects to MongoDB.
- `frontend/` — React (Vite) app. Dev server proxies `/api` to the backend.

## Getting started

```bash
npm run install:all
cp backend/.env.example backend/.env   # adjust MONGODB_URI if needed
npm run dev                            # runs backend + frontend together
```

Backend: http://localhost:5000 · Frontend: http://localhost:5173

Requires a running MongoDB instance (defaults to `mongodb://127.0.0.1:27017/monopoly_manager`).

## Board

The board is seeded with the classic 40-tile Monopoly layout on first run. Use the
**Settings** button in the app to add, edit, reorder, or remove tiles (name, type,
color group, price, rent tiers, house cost, mortgage value, tax amount).
