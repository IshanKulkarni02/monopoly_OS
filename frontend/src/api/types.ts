export interface PlayerOut {
  id: string
  name: string
  is_host: boolean
  is_banker: boolean
  balance: number
  status: 'active' | 'bankrupt' | 'left'
}

export interface PropertyOut {
  id: string
  space_index: number
  name: string
  owner_id: string | null
  price: number
  houses: number
  mortgaged: boolean
}

export interface EventLogOut {
  id: string
  kind: string
  player_ids: string[]
  payload: Record<string, unknown>
  created_at: string
}

export interface GameStateOut {
  id: string
  code: string
  name: string
  status: 'lobby' | 'active' | 'ended'
  money_mode: string
  banker_mode: 'manual' | 'auto'
  ruleset: Record<string, unknown>
  players: PlayerOut[]
  properties: PropertyOut[]
  recent_log: EventLogOut[]
}

export interface GameCreateResponse {
  game: GameStateOut
  host_player_id: string
  host_token: string
  player_token: string
}

export interface JoinGameResponse {
  game: GameStateOut
  player_id: string
  player_token: string
}

export interface LandOutcome {
  outcome: string
  message?: string
  amount?: number
  paid_to?: string
  property_id?: string
  property_name?: string
  price?: number
  transaction_id?: string
  space_type?: string
}
