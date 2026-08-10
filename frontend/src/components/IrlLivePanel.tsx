import { useEffect, useState } from 'react'
import { BoardMap } from './BoardMap'
import { PlayerTabs } from './PlayerTabs'
import { useFormatMoney } from '../hooks/useBoard'
import {
  endTurn,
  getPlayerTokens,
  movePlayer,
  purchaseProperty,
  rollForOrder,
  rollForPlayer,
  swapPlayers,
} from '../api/client'
import type { GameStateOut, RollOutcome } from '../api/types'

function landingMessage(outcome: RollOutcome, formatMoney: (amount: number) => string): string | null {
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
      message = 'Already owns this property'
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
    case 'vacation_pot':
      message = `Collected the ${formatMoney(landing.amount ?? 0)} Free Parking pot!`
      break
    default:
      message = ''
  }
  if (landing.event) {
    message += message ? ` ${landing.event.text}` : landing.event.text
  }
  return message || null
}

export function IrlLivePanel({
  code,
  state,
  myPlayerId,
  hostToken,
  playerToken,
  isHost,
}: {
  code: string
  state: GameStateOut
  myPlayerId: string
  hostToken?: string
  playerToken: string
  isHost: boolean
}) {
  const formatMoney = useFormatMoney()
  const diceCount = state.ruleset.dice_count ?? 2
  const [selectedId, setSelectedId] = useState<string>(state.current_turn_player_id || myPlayerId)
  const [diceInputs, setDiceInputs] = useState<string[]>(Array.from({ length: diceCount }, () => ''))
  const [orderRollInput, setOrderRollInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRoll, setLastRoll] = useState<RollOutcome | null>(null)
  const [lastOrderMessage, setLastOrderMessage] = useState<string | null>(null)
  const [playerTokens, setPlayerTokens] = useState<Record<string, string>>({})
  const [gmMode, setGmMode] = useState<'none' | 'move' | 'swap-pick-b'>('none')
  const [swapFirstId, setSwapFirstId] = useState<string | null>(null)

  useEffect(() => {
    setDiceInputs(Array.from({ length: diceCount }, () => ''))
  }, [diceCount])

  useEffect(() => {
    if (isHost && hostToken) {
      getPlayerTokens(code, hostToken)
        .then(setPlayerTokens)
        .catch(() => {})
    }
  }, [isHost, hostToken, code, state.players.length])

  useEffect(() => {
    if (state.current_turn_player_id) setSelectedId(state.current_turn_player_id)
  }, [state.current_turn_player_id])

  function actor() {
    if (isHost && hostToken) return { hostToken }
    return { playerId: myPlayerId, playerToken }
  }

  function tokenFor(playerId: string): string | null {
    if (playerId === myPlayerId) return playerToken
    return playerTokens[playerId] ?? null
  }

  async function guarded(fn: () => Promise<unknown>) {
    setError(null)
    setBusy(true)
    try {
      await fn()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const activePlayers = state.players.filter((p) => p.status === 'active')
  const rolledIds = new Set(state.pending_turn_order_rolls.map((r) => r.player_id))
  const waitingOn = activePlayers.filter((p) => !rolledIds.has(p.id))

  if (state.turn_order.length === 0) {
    return (
      <div className="flex flex-col gap-4">
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <p className="text-sm font-bold uppercase tracking-wide text-ink-soft">Setting turn order</p>
          <p className="mt-1 text-sm text-ink">
            Each player rolls a physical die — tap their name, enter what they rolled.{' '}
            {state.ruleset.turn_order_mode === 'entry_order'
              ? 'Whoever is entered first goes first.'
              : 'Highest roll goes first; ties re-roll.'}
          </p>
        </div>

        <PlayerTabs players={activePlayers} selectedId={selectedId} onSelect={setSelectedId} />

        {rolledIds.has(selectedId) ? (
          <p className="text-sm font-semibold text-monopoly-green">
            {state.players.find((p) => p.id === selectedId)?.name} already rolled —{' '}
            {state.pending_turn_order_rolls.find((r) => r.player_id === selectedId)?.roll}
          </p>
        ) : (
          <div className="flex gap-2">
            <input
              type="number"
              min={1}
              placeholder="What did they roll?"
              value={orderRollInput}
              onChange={(e) => setOrderRollInput(e.target.value)}
              className="w-full rounded border-2 border-ink bg-board-card p-2 text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
            />
            <button
              disabled={busy || !orderRollInput}
              onClick={() =>
                guarded(async () => {
                  const res = await rollForOrder(code, actor(), { playerId: selectedId, roll: Number(orderRollInput) })
                  setOrderRollInput('')
                  if (res.outcome.outcome === 'tie') {
                    setLastOrderMessage(`Tie at ${res.outcome.roll} between ${res.outcome.tied_players.join(' & ')} — re-roll those two.`)
                  } else if (res.outcome.outcome === 'order_set') {
                    setLastOrderMessage(null)
                  } else {
                    setLastOrderMessage(null)
                  }
                })
              }
              className="rounded border-2 border-ink bg-monopoly-green px-4 py-2 font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
            >
              Record
            </button>
          </div>
        )}

        {waitingOn.length > 0 && (
          <p className="text-xs font-semibold text-ink-soft">Still waiting on: {waitingOn.map((p) => p.name).join(', ')}</p>
        )}
        {lastOrderMessage && <p className="text-sm font-semibold text-monopoly-red">{lastOrderMessage}</p>}
        {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}

        <BoardMap players={state.players} defaultCollapsed />
      </div>
    )
  }

  const currentPlayer = state.players.find((p) => p.id === state.current_turn_player_id)
  const selectedPlayer = state.players.find((p) => p.id === selectedId)
  const isCurrentTurnSelected = selectedId === state.current_turn_player_id
  const message = lastRoll ? landingMessage(lastRoll, formatMoney) : null
  const pendingProperty = lastRoll?.landing?.property_id
    ? state.properties.find((p) => p.id === lastRoll.landing!.property_id)
    : undefined
  const canBuy = lastRoll?.landing?.outcome === 'purchasable' && pendingProperty?.owner_id == null

  return (
    <div className="flex flex-col gap-4">
      <PlayerTabs players={activePlayers} selectedId={selectedId} currentTurnPlayerId={state.current_turn_player_id} onSelect={setSelectedId} />

      {isCurrentTurnSelected ? (
        <div className="flex flex-col gap-3 rounded border-2 border-monopoly-green bg-monopoly-green/10 p-3">
          <p className="text-sm font-bold uppercase tracking-wide text-monopoly-green-dark">{currentPlayer?.name}'s turn</p>
          {selectedPlayer?.in_jail && <p className="text-sm font-bold text-monopoly-red">In jail (attempt {selectedPlayer.jail_turns + 1} of 3)</p>}

          <div className="flex flex-wrap gap-2">
            {diceInputs.map((val, i) => (
              <input
                key={i}
                type="number"
                min={1}
                max={6}
                placeholder={`Die ${i + 1}`}
                value={val}
                onChange={(e) => setDiceInputs(diceInputs.map((v, idx) => (idx === i ? e.target.value : v)))}
                className="w-20 rounded border-2 border-ink bg-board-card p-2 text-center text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
              />
            ))}
          </div>
          <button
            disabled={busy || diceInputs.some((v) => !v)}
            onClick={() =>
              guarded(async () => {
                const dice = diceInputs.map(Number)
                const res = await rollForPlayer(code, actor(), { playerId: selectedId, dice })
                setLastRoll(res.result)
                setDiceInputs(Array.from({ length: diceCount }, () => ''))
              })
            }
            className="rounded border-2 border-ink bg-monopoly-green py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-green-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none"
          >
            Enter roll
          </button>

          {lastRoll && (
            <div className="rounded border-2 border-ink bg-board-card p-3 text-sm">
              <p className="font-mono text-lg font-bold text-ink">
                🎲 {lastRoll.dice.join(' + ')}
                {lastRoll.doubles ? ' (doubles!)' : ''}
              </p>
              {lastRoll.outcome === 'stayed_in_jail' && <p className="mt-1 font-bold text-monopoly-red">No doubles — still stuck in jail.</p>}
              {message && <p className="mt-1 font-semibold text-ink">{message}</p>}
              {canBuy && (
                <button
                  disabled={busy}
                  onClick={() =>
                    guarded(async () => {
                      const tok = tokenFor(selectedId)
                      if (!tok) throw new Error("Don't have that player's token yet")
                      await purchaseProperty(code, selectedId, tok, lastRoll.landing!.property_id!)
                    })
                  }
                  className="mt-2 rounded border-2 border-ink bg-monopoly-green px-3 py-1.5 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
                >
                  Buy for {formatMoney(lastRoll.landing!.price ?? 0)}
                </button>
              )}
            </div>
          )}

          <button
            disabled={busy}
            onClick={() =>
              guarded(async () => {
                const tok = tokenFor(selectedId)
                if (!tok) throw new Error("Don't have that player's token yet")
                await endTurn(code, selectedId, tok)
                setLastRoll(null)
              })
            }
            className="rounded border-2 border-ink bg-board-card py-2 text-sm font-bold text-ink hover:bg-board disabled:opacity-50"
          >
            End turn
          </button>
        </div>
      ) : (
        <p className="text-center text-sm font-semibold text-ink-soft">Waiting for {currentPlayer?.name ?? '…'} to play</p>
      )}

      {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}

      {isHost && (
        <div className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
          <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">GM tools — {selectedPlayer?.name}</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setGmMode(gmMode === 'move' ? 'none' : 'move')}
              className={`rounded border-2 border-ink px-3 py-1.5 text-sm font-bold ${gmMode === 'move' ? 'bg-monopoly-gold text-ink' : 'text-ink hover:bg-board'}`}
            >
              Move to tile…
            </button>
            <button
              onClick={() => {
                setSwapFirstId(selectedId)
                setGmMode('swap-pick-b')
              }}
              className={`rounded border-2 border-ink px-3 py-1.5 text-sm font-bold ${gmMode === 'swap-pick-b' ? 'bg-monopoly-gold text-ink' : 'text-ink hover:bg-board'}`}
            >
              Swap {selectedPlayer?.name} with…
            </button>
          </div>

          {gmMode === 'swap-pick-b' && swapFirstId && (
            <div className="flex flex-wrap gap-2">
              {activePlayers
                .filter((p) => p.id !== swapFirstId)
                .map((p) => (
                  <button
                    key={p.id}
                    disabled={busy}
                    onClick={() =>
                      guarded(async () => {
                        if (!hostToken) return
                        await swapPlayers(code, hostToken, swapFirstId, p.id)
                        setGmMode('none')
                        setSwapFirstId(null)
                      })
                    }
                    className="rounded border-2 border-ink bg-board px-3 py-1.5 text-sm font-bold text-ink hover:bg-monopoly-gold"
                  >
                    Swap with {p.name}
                  </button>
                ))}
            </div>
          )}

          {gmMode === 'move' && (
            <BoardMap
              players={state.players}
              pickMode
              pickLabel={`Move ${selectedPlayer?.name} to…`}
              onPickTile={(position) =>
                guarded(async () => {
                  if (!hostToken) return
                  await movePlayer(code, hostToken, { playerId: selectedId, position })
                  setGmMode('none')
                })
              }
            />
          )}
        </div>
      )}

      {gmMode !== 'move' && <BoardMap players={state.players} defaultCollapsed />}
    </div>
  )
}
