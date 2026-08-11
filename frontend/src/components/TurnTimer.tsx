import { useEffect, useState } from 'react'
import type { PlayerOut } from '../api/types'

export function TurnTimer({
  turnStartedAt,
  turnTimerSeconds,
  currentPlayer,
  isHost,
  busy,
  onForceEndTurn,
}: {
  turnStartedAt: string | null
  turnTimerSeconds: number
  currentPlayer: PlayerOut | undefined
  isHost: boolean
  busy: boolean
  onForceEndTurn: () => void
}) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  if (turnTimerSeconds <= 0 || !turnStartedAt) return null

  const deadline = new Date(turnStartedAt).getTime() + turnTimerSeconds * 1000
  const remaining = Math.max(0, Math.round((deadline - now) / 1000))
  const expired = remaining <= 0
  const minutes = Math.floor(remaining / 60)
  const seconds = remaining % 60

  return (
    <div className={`mb-3 flex items-center justify-between rounded border-2 border-ink p-2 ${expired ? 'bg-monopoly-red text-white' : 'bg-board-card text-ink'}`}>
      <span className="text-sm font-bold">
        {expired ? `Time's up — ${currentPlayer?.name ?? 'current player'}'s turn` : `⏱ ${currentPlayer?.name ?? '…'}: ${minutes}:${String(seconds).padStart(2, '0')}`}
      </span>
      {expired && isHost && (
        <button
          disabled={busy}
          onClick={onForceEndTurn}
          className="rounded border-2 border-white px-2 py-1 text-xs font-bold text-white hover:bg-monopoly-red-dark disabled:opacity-50"
        >
          Force end turn
        </button>
      )}
    </div>
  )
}
