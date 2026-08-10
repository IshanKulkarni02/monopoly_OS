export interface PlayerOut {
  id: string
  name: string
  is_host: boolean
  is_banker: boolean
  balance: number
  status: 'active' | 'bankrupt' | 'left'
  jail_free_cards: number
  position: number
  in_jail: boolean
  jail_turns: number
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

export interface TransactionOut {
  id: string
  type: string
  from_player_id: string | null
  to_player_id: string | null
  amount: number
  reason: string
  created_by_player_id: string | null
  reversed: boolean
  status: 'pending' | 'confirmed' | 'declined'
  created_at: string
}

export type MoneyMode = 'banker_ledger' | 'cash_counter' | 'digital_transfer'
export type EventSystem = 'cards' | 'wheel'
export type PlayMode = 'irl_companion' | 'virtual'

export interface GameStateOut {
  id: string
  code: string
  name: string
  status: 'lobby' | 'active' | 'ended'
  money_mode: MoneyMode
  banker_mode: 'manual' | 'auto'
  play_mode: PlayMode
  ruleset: {
    starting_cash: number
    pass_go_bonus: number
    free_parking_pot: boolean
    event_system: EventSystem
    challenge_before_buy: { enabled: boolean; type: string }
    inflation: { enabled: boolean; trigger: 'on_pass_go' | 'per_round'; rate: number; scope: string[] }
  }
  inflation_multiplier: number
  round_number: number
  turn_order: string[]
  current_turn_player_id: string | null
  players: PlayerOut[]
  properties: PropertyOut[]
  recent_log: EventLogOut[]
  pending_transfers: TransactionOut[]
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

export interface DrawEventOutcome {
  kind: string
  text: string
  amount: number
  transaction_ids: string[]
}

export interface PurchaseResult {
  purchased: boolean
  challenge: { type: string; roll: number; passed: boolean } | null
  game: GameStateOut
}

export interface RollOutcome {
  outcome: 'moved' | 'stayed_in_jail'
  dice: [number, number]
  doubles?: boolean
  position?: number
  landing?: LandOutcome & { event?: DrawEventOutcome }
}

export interface RollResult {
  result: RollOutcome
  game: GameStateOut
}
