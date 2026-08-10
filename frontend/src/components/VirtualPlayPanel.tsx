import { useState } from 'react'
import { formatMoney, spaceByIndex } from '../boardData'
import type { PlayerOut, PropertyOut, RollOutcome } from '../api/types'

function landingMessage(outcome: RollOutcome): string | null {
  const landing = outcome.landing
  if (!landing) return null
  let message: string
  switch (landing.outcome) {
    case 'rent_paid':
      message = `Paid ${formatMoney(landing.amount ?? 0)} rent to ${landing.paid_to}`
      break
    case 'tax_paid':
      message = `Paid ${formatMoney(landing.amount ?? 0)} tax`
      break
    case 'go_bonus':
      message = `Collected ${formatMoney(landing.amount ?? 0)} for landing on GO`
      break
    case 'purchasable':
      message = `${landing.property_name} is unowned — ${formatMoney(landing.price ?? 0)}`
      break
    case 'own_property':
      message = 'You already own this property'
      break
    case 'mortgaged_no_rent':
      message = 'This property is mortgaged — no rent due'
      break
    case 'needs_manual':
      message = landing.message || 'Ask the banker to resolve this manually'
      break
    case 'sent_to_jail':
      message = 'Busted — sent straight to jail!'
      break
    default:
      message = ''
  }
  if (landing.event) {
    message += message ? ` ${landing.event.text}` : landing.event.text
  }
  return message || null
}

export function VirtualPlayPanel({
  players,
  properties,
  myPlayerId,
  currentTurnPlayerId,
  busy,
  error,
  lastRoll,
  onRoll,
  onEndTurn,
  onPurchase,
}: {
  players: PlayerOut[]
  properties: PropertyOut[]
  myPlayerId: string
  currentTurnPlayerId: string | null
  busy: boolean
  error: string | null
  lastRoll: RollOutcome | null
  onRoll: (opts: { useJailFreeCard?: boolean; payFine?: boolean }) => void
  onEndTurn: () => void
  onPurchase: (propertyId: string) => void
}) {
  const [jailChoice, setJailChoice] = useState<'roll' | 'card' | 'fine'>('roll')
  const me = players.find((p) => p.id === myPlayerId)!
  const isMyTurn = currentTurnPlayerId === myPlayerId
  const currentPlayer = players.find((p) => p.id === currentTurnPlayerId)
  const mySpace = spaceByIndex(me.position)
  const message = lastRoll ? landingMessage(lastRoll) : null

  // Re-check against live property state rather than trusting the frozen
  // roll snapshot, so the Buy button/message disappear the moment the
  // purchase (or anyone else's) actually lands.
  const pendingProperty = lastRoll?.landing?.property_id
    ? properties.find((p) => p.id === lastRoll.landing!.property_id)
    : undefined
  const canStillBuy = lastRoll?.landing?.outcome === 'purchasable' && pendingProperty?.owner_id == null

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1.5">
        {players.map((p) => (
          <span
            key={p.id}
            className={`rounded-full border-2 border-ink px-2.5 py-1 text-xs font-bold ${
              p.id === currentTurnPlayerId ? 'bg-monopoly-green text-white' : 'bg-board-card text-ink-soft'
            }`}
          >
            {p.name}
          </span>
        ))}
      </div>

      <div className="rounded border-2 border-ink bg-board-card p-3">
        <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Your space</p>
        <p className="font-display text-lg tracking-wide text-ink">{mySpace.name}</p>
        {me.in_jail && <p className="mt-1 text-sm font-bold text-monopoly-red">In jail (attempt {me.jail_turns + 1} of 3)</p>}
      </div>

      {isMyTurn ? (
        <div className="flex flex-col gap-3 rounded border-2 border-monopoly-green bg-monopoly-green/10 p-3">
          <p className="text-sm font-bold uppercase tracking-wide text-monopoly-green-dark">It's your turn!</p>

          {me.in_jail && (
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">Get out of jail…</label>
              <select
                value={jailChoice}
                onChange={(e) => setJailChoice(e.target.value as 'roll' | 'card' | 'fine')}
                className="rounded border-2 border-ink bg-board-card p-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
              >
                <option value="roll">Try to roll doubles</option>
                {me.jail_free_cards > 0 && <option value="card">Use a jail-free card ({me.jail_free_cards})</option>}
                <option value="fine">Pay $50 fine</option>
              </select>
            </div>
          )}

          <button
            disabled={busy}
            onClick={() =>
              onRoll({
                useJailFreeCard: me.in_jail && jailChoice === 'card',
                payFine: me.in_jail && jailChoice === 'fine',
              })
            }
            className="rounded border-2 border-ink bg-monopoly-green py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-green-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none"
          >
            Roll dice
          </button>

          {lastRoll && (
            <div className="rounded border-2 border-ink bg-board-card p-3 text-sm">
              <p className="font-mono text-lg font-bold text-ink">
                🎲 {lastRoll.dice[0]} + {lastRoll.dice[1]}
                {lastRoll.doubles ? ' (doubles!)' : ''}
              </p>
              {lastRoll.outcome === 'stayed_in_jail' && <p className="mt-1 font-bold text-monopoly-red">No doubles — still stuck in jail.</p>}
              {lastRoll.landing?.outcome === 'purchasable' && !canStillBuy ? (
                <p className="mt-1 font-semibold text-monopoly-green">
                  {pendingProperty?.owner_id === myPlayerId ? `You bought ${pendingProperty.name}!` : `${pendingProperty?.name} was purchased.`}
                </p>
              ) : (
                message && <p className="mt-1 font-semibold text-ink">{message}</p>
              )}
              {canStillBuy && (
                <button
                  disabled={busy}
                  onClick={() => onPurchase(lastRoll.landing!.property_id!)}
                  className="mt-2 rounded border-2 border-ink bg-monopoly-green px-3 py-1.5 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
                >
                  Buy for {formatMoney(lastRoll.landing!.price ?? 0)}
                </button>
              )}
            </div>
          )}

          {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}

          <button
            disabled={busy}
            onClick={onEndTurn}
            className="rounded border-2 border-ink bg-board-card py-2 text-sm font-bold text-ink hover:bg-board disabled:opacity-50"
          >
            End turn
          </button>
        </div>
      ) : (
        <p className="text-center text-sm font-semibold text-ink-soft">Waiting for {currentPlayer?.name ?? '…'} to play</p>
      )}
    </div>
  )
}
