import { handle } from "./api";

const BASE = "/api/games";

function get(url) {
  return fetch(url).then(handle);
}

function post(url, data) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data ?? {}),
  }).then(handle);
}

function put(url, data) {
  return fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data ?? {}),
  }).then(handle);
}

export function listGames() {
  return get(BASE);
}

export function getVariants() {
  return get(`${BASE}/variants`);
}

export function createGame(data) {
  return post(BASE, data);
}

export function getGame(id) {
  return get(`${BASE}/${id}`);
}

export function deleteGame(id) {
  return fetch(`${BASE}/${id}`, { method: "DELETE" }).then((res) => {
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
  });
}

export function addPlayer(gameId, data) {
  return post(`${BASE}/${gameId}/players`, data);
}

export function movePlayer(gameId, playerId, steps) {
  return put(`${BASE}/${gameId}/players/${playerId}/move`, { steps });
}

export function setPlayerPosition(gameId, playerId, position) {
  return put(`${BASE}/${gameId}/players/${playerId}/position`, { position });
}

export function setPlayerJail(gameId, playerId, inJail) {
  return put(`${BASE}/${gameId}/players/${playerId}/jail`, { inJail });
}

export function setDiceMode(gameId, diceMode) {
  return put(`${BASE}/${gameId}/dice-mode`, { diceMode });
}

export function endTurn(gameId, playerId) {
  return put(`${BASE}/${gameId}/players/${playerId}/end-turn`);
}

export function getTransactions(gameId) {
  return get(`${BASE}/${gameId}/transactions`);
}

export function createTransaction(gameId, data) {
  return post(`${BASE}/${gameId}/transactions`, data);
}

export function buyProperty(gameId, position, playerId) {
  return post(`${BASE}/${gameId}/properties/${position}/buy`, { playerId });
}

export function auctionProperty(gameId, position, playerId, amount) {
  return post(`${BASE}/${gameId}/properties/${position}/auction`, { playerId, amount });
}

export function mortgageProperty(gameId, position) {
  return post(`${BASE}/${gameId}/properties/${position}/mortgage`);
}

export function unmortgageProperty(gameId, position) {
  return post(`${BASE}/${gameId}/properties/${position}/unmortgage`);
}

export function buildHouse(gameId, position) {
  return post(`${BASE}/${gameId}/properties/${position}/build-house`);
}

export function sellHouse(gameId, position) {
  return post(`${BASE}/${gameId}/properties/${position}/sell-house`);
}

export function getDebts(gameId) {
  return get(`${BASE}/${gameId}/debts`);
}

export function createDebt(gameId, data) {
  return post(`${BASE}/${gameId}/debts`, data);
}

export function settleDebt(gameId, debtId) {
  return post(`${BASE}/${gameId}/debts/${debtId}/settle`);
}

export function claimFreeParking(gameId, playerId) {
  return post(`${BASE}/${gameId}/free-parking/claim`, { playerId });
}
