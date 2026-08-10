import type { GameCreateResponse, GameStateOut, JoinGameResponse, LandOutcome } from './types'

class ApiError extends Error {}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.detail || `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export function createGame(input: {
  hostName: string
  name?: string
  startingCash?: number
  bankerMode: 'manual' | 'auto'
}): Promise<GameCreateResponse> {
  return request('/api/games', {
    method: 'POST',
    body: JSON.stringify({
      host_name: input.hostName,
      name: input.name || 'Monopoly Night',
      starting_cash: input.startingCash,
      banker_mode: input.bankerMode,
    }),
  })
}

export function joinGame(code: string, name: string): Promise<JoinGameResponse> {
  return request(`/api/games/${code}/join`, { method: 'POST', body: JSON.stringify({ name }) })
}

export function getGame(code: string): Promise<GameStateOut> {
  return request(`/api/games/${code}`)
}

export function startGame(code: string, hostToken: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/start`, { method: 'POST', headers: { 'x-host-token': hostToken } })
}

export function setBanker(code: string, hostToken: string, playerId: string, isBanker: boolean): Promise<GameStateOut> {
  return request(`/api/games/${code}/banker`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken },
    body: JSON.stringify({ player_id: playerId, is_banker: isBanker }),
  })
}

export function logTransaction(
  code: string,
  playerId: string,
  playerToken: string,
  input: { fromPlayerId: string | null; toPlayerId: string | null; amount: number; reason: string },
): Promise<GameStateOut> {
  return request(`/api/games/${code}/transactions`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({
      from_player_id: input.fromPlayerId,
      to_player_id: input.toPlayerId,
      amount: input.amount,
      reason: input.reason,
    }),
  })
}

export function reverseTransaction(
  code: string,
  playerId: string,
  playerToken: string,
  transactionId: string,
): Promise<GameStateOut> {
  return request(`/api/games/${code}/transactions/${transactionId}/reverse`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function purchaseProperty(
  code: string,
  playerId: string,
  playerToken: string,
  propertyId: string,
): Promise<GameStateOut> {
  return request(`/api/games/${code}/properties/${propertyId}/purchase`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function declareLanding(
  code: string,
  playerToken: string,
  input: { playerId: string; spaceIndex: number; diceRoll?: number },
): Promise<{ outcome: LandOutcome; game: GameStateOut }> {
  return request(`/api/games/${code}/land`, {
    method: 'POST',
    headers: { 'x-player-token': playerToken },
    body: JSON.stringify({ player_id: input.playerId, space_index: input.spaceIndex, dice_roll: input.diceRoll }),
  })
}

export function getPlayerLog(code: string, playerId: string) {
  return request(`/api/games/${code}/players/${playerId}/log`)
}

export { ApiError }
