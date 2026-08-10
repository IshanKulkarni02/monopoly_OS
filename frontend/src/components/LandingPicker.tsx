import { useState } from 'react'
import { CLASSIC_BOARD, formatMoney } from '../boardData'
import type { LandOutcome } from '../api/types'

function outcomeMessage(outcome: LandOutcome): string {
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
  const [spaceIndex, setSpaceIndex] = useState(1)
  const [diceRoll, setDiceRoll] = useState('')

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
      <label className="text-xs text-neutral-400">I landed on…</label>
      <select
        value={spaceIndex}
        onChange={(e) => setSpaceIndex(Number(e.target.value))}
        className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
      >
        {CLASSIC_BOARD.map((s) => (
          <option key={s.index} value={s.index}>{s.name}</option>
        ))}
      </select>
      <input
        type="number"
        placeholder="Dice roll (only needed for utilities)"
        value={diceRoll}
        onChange={(e) => setDiceRoll(e.target.value)}
        className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
      />
      <button
        disabled={busy}
        onClick={() => onDeclare(spaceIndex, diceRoll ? Number(diceRoll) : undefined)}
        className="rounded-lg bg-emerald-700 py-2 font-medium hover:bg-emerald-600 disabled:opacity-50"
      >
        Confirm landing
      </button>
      {lastOutcome && <p className="text-sm text-neutral-200">{outcomeMessage(lastOutcome)}</p>}
    </div>
  )
}
