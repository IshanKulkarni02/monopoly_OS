import type { BoardGroupOut, BoardTileOut, CurrencyConfig } from './api/types'

export const DEFAULT_CURRENCY: CurrencyConfig = {
  symbol: '$',
  denominations: [1, 5, 10, 20, 50, 100],
  track_denominations: false,
}

export function tileAtPosition(tiles: BoardTileOut[], position: number): BoardTileOut | undefined {
  const size = tiles.length
  if (!size) return undefined
  const normalized = ((position % size) + size) % size
  return tiles.find((t) => t.position === normalized)
}

export function groupById(groups: BoardGroupOut[], groupId: string | null | undefined): BoardGroupOut | undefined {
  if (!groupId) return undefined
  return groups.find((g) => g.id === groupId)
}

export function groupPositions(tiles: BoardTileOut[], groupId: string | null | undefined): number[] {
  if (!groupId) return []
  return tiles.filter((t) => t.group_id === groupId).map((t) => t.position)
}

export function formatMoney(amount: number, symbol: string = DEFAULT_CURRENCY.symbol): string {
  return `${symbol}${amount.toLocaleString()}`
}

export function denominationSummary(denominations: Record<string, number>, symbol: string): string | null {
  const entries = Object.entries(denominations)
    .filter(([, count]) => count > 0)
    .sort((a, b) => Number(b[0]) - Number(a[0]))
  if (entries.length === 0) return null
  return entries.map(([note, count]) => `${count}×${symbol}${note}`).join('  ')
}
