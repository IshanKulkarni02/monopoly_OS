export interface UserOut {
  id: string
  email: string
  name: string
}

export interface AuthResponse {
  user: UserOut
  session_token: string
}

export interface PlayerOut {
  id: string
  name: string
  is_host: boolean
  is_banker: boolean
  is_bot: boolean
  balance: number
  denominations: Record<string, number>
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

export type TileKind = 'go' | 'property' | 'mystery' | 'tax' | 'jail' | 'vacation' | 'go_to_jail' | 'custom'
export type RentModel = 'fixed_table' | 'group_count_table' | 'dice_multiplier_table'

export interface BoardGroupOut {
  id: string
  key: string
  name: string
  color: string
  rent_multiplier: number | null
}

export interface BoardTileOut {
  id: string
  position: number
  name: string
  kind: TileKind
  group_id: string | null
  price: number | null
  rent_model: RentModel
  rent_table: number[]
  upgrade_costs: number[]
  mortgage_value: number | null
  tax_config: Record<string, unknown>
  mystery_deck_key: string
  special_effects: unknown[]
}

export interface BoardSummaryOut {
  id: string
  key: string
  name: string
  description: string
  size: number
  is_preset: boolean
  owner_user_id: string | null
}

export interface BoardDetailOut extends BoardSummaryOut {
  groups: BoardGroupOut[]
  tiles: BoardTileOut[]
}

export type MoneyMode = 'banker_ledger' | 'cash_counter' | 'digital_transfer'
export type EventSystem = 'cards' | 'wheel'
export type PlayMode = 'irl_companion' | 'virtual'

export interface CurrencyConfig {
  symbol: string
  denominations: number[]
  track_denominations: boolean
}

export interface GameStateOut {
  id: string
  code: string
  name: string
  status: 'lobby' | 'active' | 'ended'
  money_mode: MoneyMode
  banker_mode: 'manual' | 'auto'
  play_mode: PlayMode
  board: BoardDetailOut
  ruleset: {
    starting_cash: number
    pass_go_bonus: number
    free_parking_pot: boolean
    event_system: EventSystem
    challenge_before_buy: { enabled: boolean; type: string }
    inflation: { enabled: boolean; trigger: 'on_pass_go' | 'per_round'; rate: number; scope: string[] }
    currency: CurrencyConfig
    mortgage_percentage: number
    group_rent_multiplier: number
    jail_fine: number
    jail_max_turns: number
    dice_count: number
    turn_order_mode: 'highest_roll_first' | 'entry_order'
    [key: string]: unknown
  }
  inflation_multiplier: number
  round_number: number
  free_parking_pot_amount: number
  turn_order: string[]
  current_turn_player_id: string | null
  pending_turn_order_rolls: { player_id: string; player_name: string; roll: number }[]
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
  dice: number[]
  doubles?: boolean
  position?: number
  landing?: LandOutcome & { event?: DrawEventOutcome }
}

export interface RollResult {
  result: RollOutcome
  game: GameStateOut
}

export type OrderRollOutcome =
  | { outcome: 'recorded'; waiting_on: string[] }
  | { outcome: 'order_set'; turn_order: string[] }
  | { outcome: 'tie'; tied_players: string[]; roll: number }

export interface OrderRollResult {
  outcome: OrderRollOutcome
  game: GameStateOut
}

