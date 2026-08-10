import { useState } from 'react'
import { useBoard, useFormatMoney } from '../hooks/useBoard'
import type { LandOutcome } from '../api/types'

function outcomeMessage(outcome: LandOutcome, formatMoney: (amount: number) => string): string {
  switch (outcome.outcome) {
    case 'rent_paid':
      return `Paid ${formatMoney(outcome.amount ?? 0)} rent to ${outcome.paid_to}`
    case 'tax_paid':
      return `Paid ${formatMoney(outcome.amount ?? 0)} tax`
    case 'go_bonus':
      return `Collected ${formatMoney(outcome.amount ?? 0)} for passing GO`
    case 'purchasable':
      return `${outcome.property_name} is unowned — buy it from the Board tab for ${formatMoney(outcome.price ?? 0)}`
    case 'own_property':
      return 'You already own this property — no rent due'
    case 'mortgaged_no_rent':
      return 'This property is mortgaged — no rent due'
    case 'needs_manual':
      return outcome.message || 'Enter the dice roll to compute utility rent'
    case 'no_action':
      return "Nothing to do on this space"
    default:
      return outcome.message || outcome.outcome
  }
}

export function LandingPicker({
  onDeclare,
  busy,
  lastOutcome,
}: {
  onDeclare: (spaceIndex: number, diceRoll?: number) => void
  busy: boolean
  lastOutcome: LandOutcome | null
}) {
  const formatMoney = useFormatMoney()
  const { tiles } = useBoard()
  const [spaceIndex, setSpaceIndex] = useState(tiles[1]?.position ?? 0)
  const [diceRoll, setDiceRoll] = useState('')

  return (
    <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-3">
      <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">I landed on…</label>
      <select
        value={spaceIndex}
        onChange={(e) => setSpaceIndex(Number(e.target.value))}
        className="w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
      >
        {tiles.map((t) => (
          <option key={t.position} value={t.position}>{t.name}</option>
        ))}
      </select>
      <input
        type="number"
        placeholder="Dice roll (only needed for utilities)"
        value={diceRoll}
        onChange={(e) => setDiceRoll(e.target.value)}
        className="w-full rounded border-2 border-ink bg-board-card p-2 text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
      />
      <button
        disabled={busy}
        onClick={() => onDeclare(spaceIndex, diceRoll ? Number(diceRoll) : undefined)}
        className="rounded border-2 border-ink bg-monopoly-green py-2 font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
      >
        Confirm landing
      </button>
      {lastOutcome && <p className="text-sm font-semibold text-ink">{outcomeMessage(lastOutcome, formatMoney)}</p>}
    </div>
  )
}
