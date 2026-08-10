# Builds one deployable artifact: the FastAPI backend serving the built
# React frontend on a single port. Works the same whether it ends up
# running on a laptop for game night or on a server.

FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN pip install --no-cache-dir uv
WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist ../frontend/dist

ENV DATABASE_URL=sqlite:////data/monopoly.db
RUN mkdir -p /data
VOLUME /data

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
