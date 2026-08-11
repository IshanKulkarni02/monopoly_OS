import type {
  AuthResponse,
  BoardDetailOut,
  BoardSummaryOut,
  DrawEventOutcome,
  EventLogOut,
  EventSystem,
  GameCreateResponse,
  GameStateOut,
  GameStats,
  JoinGameResponse,
  LandOutcome,
  MoneyMode,
  OrderRollResult,
  PlayMode,
  PurchaseResult,
  RollResult,
  TradeOut,
  UserOut,
} from './types'

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
  boardKey?: string
  startingCash?: number
  bankerMode: 'manual' | 'auto'
  playMode: PlayMode
  moneyMode: MoneyMode
  eventSystem: EventSystem
  freeParkingPot: boolean
  challengeBeforeBuy: boolean
  inflationEnabled: boolean
  inflationTrigger: 'on_pass_go' | 'per_round'
  inflationRate: number
  diceCount: number
  turnOrderMode: 'highest_roll_first' | 'entry_order'
  mysteryDeckMode: 'probability' | 'finite'
  trackDenominations: boolean
  auctionEnabled?: boolean
  tradingEnabled?: boolean
  turnTimerSeconds?: number
  sessionToken?: string | null
}): Promise<GameCreateResponse> {
  return request('/api/games', {
    method: 'POST',
    headers: input.sessionToken ? { 'x-session-token': input.sessionToken } : {},
    body: JSON.stringify({
      host_name: input.hostName,
      name: input.name || 'Monopoly Night',
      board_key: input.boardKey || null,
      starting_cash: input.startingCash,
      banker_mode: input.bankerMode,
      play_mode: input.playMode,
      money_mode: input.moneyMode,
      event_system: input.eventSystem,
      free_parking_pot: input.freeParkingPot,
      challenge_before_buy: input.challengeBeforeBuy,
      inflation_enabled: input.inflationEnabled,
      inflation_trigger: input.inflationTrigger,
      inflation_rate: input.inflationRate,
      dice_count: input.diceCount,
      turn_order_mode: input.turnOrderMode,
      mystery_deck_mode: input.mysteryDeckMode,
      track_denominations: input.trackDenominations,
      turn_timer_seconds: input.turnTimerSeconds ?? 0,
      auction_enabled: input.auctionEnabled ?? false,
      trading_enabled: input.tradingEnabled ?? true,
    }),
  })
}

export function listBoards(sessionToken?: string | null): Promise<BoardSummaryOut[]> {
  return request('/api/boards', { headers: sessionToken ? { 'x-session-token': sessionToken } : {} })
}

export function getBoard(key: string): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}`)
}

// --- Board editor: every call needs the owner's session token ---

export function duplicateBoard(
  sourceKey: string,
  sessionToken: string,
  input: { key: string; name: string; description: string },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${sourceKey}/duplicate`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(input),
  })
}

export function updateBoard(
  key: string,
  sessionToken: string,
  input: { name?: string; description?: string },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}`, {
    method: 'PATCH',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(input),
  })
}

export function deleteBoardTemplate(key: string, sessionToken: string): Promise<{ status: string }> {
  return request(`/api/boards/${key}`, { method: 'DELETE', headers: { 'x-session-token': sessionToken } })
}

export interface TileFieldsInput {
  name?: string
  kind?: string
  group_id?: string | null
  price?: number | null
  rent_model?: string
  rent_table?: number[]
  upgrade_costs?: number[]
  mortgage_value?: number | null
  tax_config?: Record<string, unknown>
  mystery_deck_key?: string
  special_effects?: unknown[]
  locked?: boolean
}

export function insertTile(
  key: string,
  sessionToken: string,
  input: { position: number; name: string; kind: string; fields?: TileFieldsInput },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/tiles`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify({ position: input.position, name: input.name, kind: input.kind, fields: input.fields ?? {} }),
  })
}

export function updateTile(
  key: string,
  tileId: string,
  sessionToken: string,
  fields: TileFieldsInput,
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/tiles/${tileId}`, {
    method: 'PATCH',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(fields),
  })
}

export function removeTile(key: string, tileId: string, sessionToken: string): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/tiles/${tileId}`, { method: 'DELETE', headers: { 'x-session-token': sessionToken } })
}

export function moveTile(key: string, tileId: string, otherTileId: string, sessionToken: string): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/tiles/${tileId}/move`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify({ other_tile_id: otherTileId }),
  })
}

export function createGroup(
  key: string,
  sessionToken: string,
  input: { key: string; name: string; color: string; rent_multiplier?: number | null },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/groups`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(input),
  })
}

export function updateGroup(
  key: string,
  groupId: string,
  sessionToken: string,
  fields: { name?: string; color?: string; rent_multiplier?: number | null },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/groups/${groupId}`, {
    method: 'PATCH',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(fields),
  })
}

export interface MysteryCardOut {
  id: string
  deck_key: string
  text: string
  effect_kind: string
  amount: number
  target_position: number | null
  weight: number
}

export function listMysteryCards(key: string, deckKey?: string): Promise<MysteryCardOut[]> {
  return request(`/api/boards/${key}/mystery_cards${deckKey ? `?deck_key=${encodeURIComponent(deckKey)}` : ''}`)
}

export function createMysteryCard(
  key: string,
  sessionToken: string,
  input: { deck_key: string; text: string; effect_kind: string; amount: number; target_position?: number | null; weight?: number },
): Promise<MysteryCardOut> {
  return request(`/api/boards/${key}/mystery_cards`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(input),
  })
}

export function updateMysteryCard(
  key: string,
  cardId: string,
  sessionToken: string,
  fields: Partial<Omit<MysteryCardOut, 'id'>>,
): Promise<MysteryCardOut> {
  return request(`/api/boards/${key}/mystery_cards/${cardId}`, {
    method: 'PATCH',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify(fields),
  })
}

export function deleteMysteryCard(key: string, cardId: string, sessionToken: string): Promise<{ status: string }> {
  return request(`/api/boards/${key}/mystery_cards/${cardId}`, { method: 'DELETE', headers: { 'x-session-token': sessionToken } })
}

export function regenerateLayout(
  key: string,
  sessionToken: string,
  input: { groupConstraints: Record<string, { min_gap?: number | null; max_gap?: number | null }>; seed?: number | null },
): Promise<BoardDetailOut> {
  return request(`/api/boards/${key}/generate`, {
    method: 'POST',
    headers: { 'x-session-token': sessionToken },
    body: JSON.stringify({ group_constraints: input.groupConstraints, seed: input.seed ?? null }),
  })
}

export function saveBoardTemplate(
  code: string,
  hostToken: string,
  sessionToken: string,
  input: { key: string; name: string; description: string },
): Promise<BoardDetailOut> {
  return request(`/api/games/${code}/save_board_template`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken, 'x-session-token': sessionToken },
    body: JSON.stringify({ key: input.key, name: input.name, description: input.description }),
  })
}

export function signup(email: string, password: string, name: string): Promise<AuthResponse> {
  return request('/api/auth/signup', { method: 'POST', body: JSON.stringify({ email, password, name }) })
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export function logout(sessionToken: string): Promise<{ status: string }> {
  return request('/api/auth/logout', { method: 'POST', headers: { 'x-session-token': sessionToken } })
}

export function getMe(sessionToken: string): Promise<UserOut> {
  return request('/api/auth/me', { headers: { 'x-session-token': sessionToken } })
}

export function joinGame(code: string, name: string): Promise<JoinGameResponse> {
  return request(`/api/games/${code}/join`, { method: 'POST', body: JSON.stringify({ name }) })
}

export function addPlayer(code: string, hostToken: string, name: string): Promise<JoinGameResponse> {
  return request(`/api/games/${code}/players`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken },
    body: JSON.stringify({ name }),
  })
}

export function getGame(code: string): Promise<GameStateOut> {
  return request(`/api/games/${code}`)
}

export function getStats(code: string): Promise<GameStats> {
  return request(`/api/games/${code}/stats`)
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
): Promise<PurchaseResult> {
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

export function getPlayerLog(code: string, playerId: string): Promise<EventLogOut[]> {
  return request(`/api/games/${code}/players/${playerId}/log`)
}

export function advanceRound(code: string, playerId: string, playerToken: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/advance_round`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function drawEvent(
  code: string,
  playerToken: string,
  input: { playerId: string; spaceIndex: number },
): Promise<{ outcome: DrawEventOutcome; game: GameStateOut }> {
  return request(`/api/games/${code}/draw_event`, {
    method: 'POST',
    headers: { 'x-player-token': playerToken },
    body: JSON.stringify({ player_id: input.playerId, space_index: input.spaceIndex }),
  })
}

export function sendTransfer(
  code: string,
  playerId: string,
  playerToken: string,
  input: { otherPlayerId: string; amount: number; reason: string },
): Promise<GameStateOut> {
  return request(`/api/games/${code}/transfer/send`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ other_player_id: input.otherPlayerId, amount: input.amount, reason: input.reason }),
  })
}

export function requestTransfer(
  code: string,
  playerId: string,
  playerToken: string,
  input: { otherPlayerId: string; amount: number; reason: string },
): Promise<GameStateOut> {
  return request(`/api/games/${code}/transfer/request`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ other_player_id: input.otherPlayerId, amount: input.amount, reason: input.reason }),
  })
}

export function confirmTransfer(code: string, playerId: string, playerToken: string, transactionId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/transfer/${transactionId}/confirm`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function declineTransfer(code: string, playerId: string, playerToken: string, transactionId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/transfer/${transactionId}/decline`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function rollDice(
  code: string,
  playerId: string,
  playerToken: string,
  input: { useJailFreeCard?: boolean; payFine?: boolean } = {},
): Promise<RollResult> {
  return request(`/api/games/${code}/roll`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ use_jail_free_card: input.useJailFreeCard ?? false, pay_fine: input.payFine ?? false }),
  })
}

export function endTurn(code: string, playerId: string, playerToken: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/end_turn`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function mortgageProperty(code: string, playerId: string, playerToken: string, propertyId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/properties/${propertyId}/mortgage`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function unmortgageProperty(code: string, playerId: string, playerToken: string, propertyId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/properties/${propertyId}/unmortgage`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function buildHouse(code: string, playerId: string, playerToken: string, propertyId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/properties/${propertyId}/build_house`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function sellHouse(code: string, playerId: string, playerToken: string, propertyId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/properties/${propertyId}/sell_house`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function addBot(code: string, hostToken: string, name?: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/bots`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken },
    body: JSON.stringify({ name: name || null }),
  })
}

// --- IRL live-play: turn-order ceremony, host-driven rolls, GM corrections ---
// Every call here accepts EITHER a host token (host acting for any player)
// OR that specific player's own id+token (self-service, phone connected).

interface ActingAs {
  hostToken?: string | null
  playerId?: string | null
  playerToken?: string | null
}

function actingHeaders(actor: ActingAs): Record<string, string> {
  const headers: Record<string, string> = {}
  if (actor.hostToken) headers['x-host-token'] = actor.hostToken
  if (actor.playerId) headers['x-player-id'] = actor.playerId
  if (actor.playerToken) headers['x-player-token'] = actor.playerToken
  return headers
}

export function rollForOrder(code: string, actor: ActingAs, input: { playerId: string; roll: number }): Promise<OrderRollResult> {
  return request(`/api/games/${code}/roll_for_order`, {
    method: 'POST',
    headers: actingHeaders(actor),
    body: JSON.stringify({ player_id: input.playerId, roll: input.roll }),
  })
}

export function rollForPlayer(
  code: string,
  actor: ActingAs,
  input: { playerId: string; dice: number[]; useJailFreeCard?: boolean; payFine?: boolean },
): Promise<RollResult> {
  return request(`/api/games/${code}/roll_for_player`, {
    method: 'POST',
    headers: actingHeaders(actor),
    body: JSON.stringify({
      player_id: input.playerId,
      dice: input.dice,
      use_jail_free_card: input.useJailFreeCard ?? false,
      pay_fine: input.payFine ?? false,
    }),
  })
}

export function movePlayer(
  code: string,
  hostToken: string,
  input: { playerId: string; position: number; resolveLanding?: boolean },
): Promise<GameStateOut> {
  return request(`/api/games/${code}/players/${input.playerId}/move`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken },
    body: JSON.stringify({ player_id: input.playerId, position: input.position, resolve_landing: input.resolveLanding ?? true }),
  })
}

export function swapPlayers(code: string, hostToken: string, playerAId: string, playerBId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/players/swap`, {
    method: 'POST',
    headers: { 'x-host-token': hostToken },
    body: JSON.stringify({ player_a_id: playerAId, player_b_id: playerBId }),
  })
}

export function getPlayerTokens(code: string, hostToken: string): Promise<Record<string, string>> {
  return request(`/api/games/${code}/player_tokens`, { headers: { 'x-host-token': hostToken } })
}

// --- Auctions: at most one active per game, everyone bids/passes until one wins ---

export function startAuction(code: string, playerId: string, playerToken: string, propertyId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/auctions/start`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ property_id: propertyId }),
  })
}

export function bidOnAuction(code: string, playerId: string, playerToken: string, amount: number): Promise<GameStateOut> {
  return request(`/api/games/${code}/auctions/bid`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ amount }),
  })
}

export function passAuction(code: string, playerId: string, playerToken: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/auctions/pass`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function cancelAuction(code: string, hostToken: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/auctions/cancel`, { method: 'POST', headers: { 'x-host-token': hostToken } })
}

// --- Trading: propose an exchange of cash/properties/jail-free cards, the other player accepts/declines ---

export interface ProposeTradeInput {
  recipientId: string
  offerCash?: number
  offerPropertyIds?: string[]
  offerJailCards?: number
  requestCash?: number
  requestPropertyIds?: string[]
  requestJailCards?: number
}

export function proposeTrade(code: string, playerId: string, playerToken: string, input: ProposeTradeInput): Promise<TradeOut> {
  return request(`/api/games/${code}/trades`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({
      recipient_id: input.recipientId,
      offer_cash: input.offerCash ?? 0,
      offer_property_ids: input.offerPropertyIds ?? [],
      offer_jail_cards: input.offerJailCards ?? 0,
      request_cash: input.requestCash ?? 0,
      request_property_ids: input.requestPropertyIds ?? [],
      request_jail_cards: input.requestJailCards ?? 0,
    }),
  })
}

export function acceptTrade(code: string, playerId: string, playerToken: string, tradeId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/trades/${tradeId}/accept`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function declineTrade(code: string, playerId: string, playerToken: string, tradeId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/trades/${tradeId}/decline`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

export function cancelTrade(code: string, playerId: string, playerToken: string, tradeId: string): Promise<GameStateOut> {
  return request(`/api/games/${code}/trades/${tradeId}/cancel`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
  })
}

// --- Bankruptcy: liquidate everything, pay a creditor (or the bank), and drop out ---

export function declareBankruptcy(
  code: string,
  playerId: string,
  playerToken: string,
  creditorPlayerId: string | null,
): Promise<GameStateOut> {
  return request(`/api/games/${code}/declare_bankruptcy`, {
    method: 'POST',
    headers: { 'x-player-id': playerId, 'x-player-token': playerToken },
    body: JSON.stringify({ creditor_player_id: creditorPlayerId }),
  })
}

// --- Save game / resume later: a portable JSON snapshot of playable state ---

export function exportGame(code: string, hostToken: string): Promise<Record<string, unknown>> {
  return request(`/api/games/${code}/export`, { headers: { 'x-host-token': hostToken } })
}

export function importGame(data: Record<string, unknown>): Promise<GameCreateResponse> {
  return request('/api/games/import', { method: 'POST', body: JSON.stringify({ data }) })
}

export { ApiError }
