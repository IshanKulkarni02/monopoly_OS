const BASE = "/api/tiles";

export async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json();
}

export function getTiles(boardKey = "classic") {
  return fetch(`${BASE}?board=${boardKey}`).then(handle);
}

export function createTile(data, boardKey = "classic") {
  return fetch(`${BASE}?board=${boardKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then(handle);
}

export function updateTile(id, data) {
  return fetch(`${BASE}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then(handle);
}

export function moveTile(id, direction) {
  return fetch(`${BASE}/${id}/move`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction }),
  }).then(handle);
}

export function deleteTile(id) {
  return fetch(`${BASE}/${id}`, { method: "DELETE" }).then(handle);
}
