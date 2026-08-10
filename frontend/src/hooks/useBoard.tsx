import { createContext, useContext, type ReactNode } from 'react'
import type { BoardGroupOut, BoardTileOut, CurrencyConfig } from '../api/types'
import { DEFAULT_CURRENCY, formatMoney as formatMoneyWith } from '../boardData'

interface BoardContextValue {
  tiles: BoardTileOut[]
  groups: BoardGroupOut[]
  currency: CurrencyConfig
}

const BoardContext = createContext<BoardContextValue>({ tiles: [], groups: [], currency: DEFAULT_CURRENCY })

// Wraps the active game's board (tiles + groups + currency) so any component
// can read it without every intermediate component threading it through as
// a prop — the board is per-game data now (fetched with the rest of
// GameStateOut), not a module-level constant every file could just import.
export function BoardProvider({
  tiles,
  groups,
  currency,
  children,
}: {
  tiles: BoardTileOut[]
  groups: BoardGroupOut[]
  currency: CurrencyConfig
  children: ReactNode
}) {
  return <BoardContext.Provider value={{ tiles, groups, currency }}>{children}</BoardContext.Provider>
}

export function useBoard(): BoardContextValue {
  return useContext(BoardContext)
}

export function useFormatMoney(): (amount: number) => string {
  const { currency } = useBoard()
  return (amount: number) => formatMoneyWith(amount, currency.symbol)
}
