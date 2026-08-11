import { useEffect, useState } from 'react'
import { getStats } from '../api/client'
import { useFormatMoney } from '../hooks/useBoard'
import type { GameStats } from '../api/types'

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export function StatsPanel({ code }: { code: string }) {
  const formatMoney = useFormatMoney()
  const [stats, setStats] = useState<GameStats | null>(null)

  useEffect(() => {
    let cancelled = false
    getStats(code).then((s) => { if (!cancelled) setStats(s) }).catch(() => {})
    return () => { cancelled = true }
  }, [code])

  if (!stats) return <p className="text-sm text-ink-soft">Loading stats…</p>

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Net worth ranking</h3>
        <ul className="flex flex-col gap-1.5">
          {stats.players.map((p, i) => (
            <li key={p.player_id} className="flex items-center justify-between rounded border-2 border-ink bg-board-card px-3 py-2 text-sm">
              <span className="font-bold text-ink">
                {i + 1}. {p.name} {p.status === 'bankrupt' && <span className="text-xs font-medium text-ink-soft">(bankrupt)</span>}
              </span>
              <span className="flex gap-3">
                <span className="text-xs text-ink-soft">{p.properties_owned} propert{p.properties_owned === 1 ? 'y' : 'ies'}</span>
                <span className="font-mono font-bold text-monopoly-green">{formatMoney(p.net_worth)}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Money moved</p>
          <p className="font-mono text-lg font-bold text-ink">{formatMoney(stats.total_money_moved)}</p>
        </div>
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Transactions</p>
          <p className="font-mono text-lg font-bold text-ink">{stats.total_transactions}</p>
        </div>
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Auctions won</p>
          <p className="font-mono text-lg font-bold text-ink">{stats.auctions_won}</p>
        </div>
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Trades completed</p>
          <p className="font-mono text-lg font-bold text-ink">{stats.trades_completed}</p>
        </div>
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Houses built</p>
          <p className="font-mono text-lg font-bold text-ink">{stats.houses_built}</p>
        </div>
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Bankruptcies</p>
          <p className="font-mono text-lg font-bold text-ink">{stats.bankruptcies}</p>
        </div>
      </div>

      {stats.most_valuable_property && (
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Most valuable property owned</p>
          <p className="font-bold text-ink">
            {stats.most_valuable_property.name} ({formatMoney(stats.most_valuable_property.price)})
            {stats.most_valuable_property.owner_name && ` — ${stats.most_valuable_property.owner_name}`}
          </p>
        </div>
      )}

      {stats.game_duration_seconds !== null && (
        <p className="text-center text-xs font-medium text-ink-soft">Game running for {formatDuration(stats.game_duration_seconds)}</p>
      )}
    </div>
  )
}
