import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useGameSocket } from '../hooks/useGameSocket'
import { useSession } from '../hooks/useSession'
import { JoinCodeBadge } from '../components/JoinCodeBadge'
import { PlayerList } from '../components/PlayerList'
import { PropertyBoard } from '../components/PropertyBoard'
import { BankerPanel } from '../components/BankerPanel'
import { CashCounterPanel } from '../components/CashCounterPanel'
import { TransferPanel } from '../components/TransferPanel'
import { DrawEventPanel } from '../components/DrawEventPanel'
import { LandingPicker } from '../components/LandingPicker'
import { EventFeed } from '../components/EventFeed'
import { formatMoney } from '../boardData'
import {
  joinGame,
  startGame,
  setBanker,
  logTransaction,
  reverseTransaction,
  purchaseProperty,
  declareLanding,
  drawEvent,
  sendTransfer,
  requestTransfer,
  confirmTransfer,
  declineTransfer,
  advanceRound,
  getPlayerLog,
} from '../api/client'
import type { DrawEventOutcome, EventLogOut, LandOutcome } from '../api/types'

type Tab = 'board' | 'banker' | 'transfer' | 'land' | 'draw' | 'log' | 'mylog'

export function GamePage() {
  const { code = '' } = useParams()
  const { session, saveSession: persistSession } = useSession(code)
  const { state, connected } = useGameSocket(code)
  const [tab, setTab] = useState<Tab>('board')
  const [joinName, setJoinName] = useState('')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [joinBusy, setJoinBusy] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null)
  const [lastOutcome, setLastOutcome] = useState<LandOutcome | null>(null)
  const [lastDrawOutcome, setLastDrawOutcome] = useState<DrawEventOutcome | null>(null)
  const [myLog, setMyLog] = useState<EventLogOut[]>([])

  useEffect(() => {
    if (tab === 'mylog' && session && state) {
      getPlayerLog(code, session.playerId)
        .then((log) => setMyLog(log))
        .catch(() => {})
    }
  }, [tab, session, code, state])

  if (!state) {
    return <div className="p-6 text-center text-neutral-400">Loading game…</div>
  }

  const me = session ? state.players.find((p) => p.id === session.playerId) : undefined

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault()
    setJoinError(null)
    setJoinBusy(true)
    try {
      const res = await joinGame(code, joinName.trim())
      persistSession({ code, playerId: res.player_id, playerToken: res.player_token, playerName: joinName.trim() })
    } catch (err) {
      setJoinError(err instanceof Error ? err.message : 'Could not join')
    } finally {
      setJoinBusy(false)
    }
  }

  if (!session || !me) {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
        <h1 className="text-center text-2xl font-bold text-emerald-400">{state.name}</h1>
        <p className="text-center text-sm text-neutral-400">Join code {code}</p>
        <form onSubmit={handleJoin} className="flex flex-col gap-3">
          <input
            placeholder="Your name"
            value={joinName}
            onChange={(e) => setJoinName(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-3"
          />
          {joinError && <p className="text-sm text-red-400">{joinError}</p>}
          <button
            disabled={joinBusy || !joinName}
            className="rounded-lg bg-emerald-700 py-3 font-medium hover:bg-emerald-600 disabled:opacity-50"
          >
            Join game
          </button>
        </form>
      </div>
    )
  }

  async function guarded(fn: () => Promise<unknown>) {
    setActionError(null)
    setActionBusy(true)
    try {
      await fn()
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setActionBusy(false)
    }
  }

  async function handlePurchase(propertyId: string) {
    setActionError(null)
    setPurchaseMessage(null)
    setActionBusy(true)
    try {
      const result = await purchaseProperty(code, me!.id, session!.playerToken, propertyId)
      if (result.challenge) {
        setPurchaseMessage(
          result.purchased
            ? `Challenge passed (rolled ${result.challenge.roll}) — property purchased!`
            : `Challenge failed (rolled ${result.challenge.roll}) — no purchase this time.`,
        )
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setActionBusy(false)
    }
  }

  if (state.status === 'lobby') {
    return (
      <div className="mx-auto flex min-h-screen max-w-md flex-col gap-6 p-6">
        <h1 className="text-center text-2xl font-bold">{state.name}</h1>
        <JoinCodeBadge code={state.code} />
        <div>
          <h2 className="mb-2 text-sm font-medium text-neutral-400">Players ({state.players.length})</h2>
          <PlayerList
            players={state.players}
            myPlayerId={me.id}
            canManageBanker={me.is_host}
            onToggleBanker={(playerId, next) => guarded(() => setBanker(code, session.hostToken!, playerId, next))}
          />
        </div>
        {me.is_host && (
          <button
            disabled={actionBusy || state.players.length < 2}
            onClick={() => guarded(() => startGame(code, session.hostToken!))}
            className="rounded-lg bg-emerald-700 py-3 font-medium hover:bg-emerald-600 disabled:opacity-50"
          >
            {state.players.length < 2 ? 'Need at least 2 players' : 'Start game'}
          </button>
        )}
        {actionError && <p className="text-center text-sm text-red-400">{actionError}</p>}
        {!connected && <p className="text-center text-xs text-amber-500">Reconnecting…</p>}
      </div>
    )
  }

  const myPendingRequests = state.pending_transfers.filter((t) => t.from_player_id === me.id).length
  const showBankerTab = me.is_banker && (state.money_mode === 'banker_ledger' || state.money_mode === 'cash_counter')
  const showTransferTab = state.money_mode === 'digital_transfer'
  const showAdvanceRound = me.is_banker && state.ruleset.inflation.enabled && state.ruleset.inflation.trigger === 'per_round'

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col pb-20">
      <header className="flex items-center justify-between border-b border-neutral-800 p-4">
        <div>
          <h1 className="font-bold">{state.name}</h1>
          <p className="text-xs text-neutral-500">
            Code {state.code} · {connected ? 'Live' : 'Reconnecting…'}
          </p>
          {state.ruleset.inflation.enabled && (
            <p className="text-xs text-amber-400">
              Inflation {state.inflation_multiplier.toFixed(2)}x · Round {state.round_number}
            </p>
          )}
        </div>
        <div className="text-right">
          <p className="text-xs text-neutral-500">Your balance</p>
          <p className="font-mono text-xl text-emerald-400">{formatMoney(me.balance)}</p>
          {me.jail_free_cards > 0 && <p className="text-xs text-neutral-500">{me.jail_free_cards}x jail-free card</p>}
        </div>
      </header>

      <main className="flex-1 p-4">
        {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}
        {tab === 'board' && (
          <>
            {purchaseMessage && <p className="mb-3 text-sm text-neutral-200">{purchaseMessage}</p>}
            <PropertyBoard
              properties={state.properties}
              players={state.players}
              myPlayerId={me.id}
              onPurchase={handlePurchase}
            />
          </>
        )}
        {tab === 'banker' && showBankerTab && state.money_mode === 'banker_ledger' && (
          <BankerPanel
            players={state.players}
            recentLog={state.recent_log}
            busy={actionBusy}
            error={actionError}
            onLogTransaction={(input) => guarded(() => logTransaction(code, me.id, session.playerToken, input))}
            onReverse={(transactionId) => guarded(() => reverseTransaction(code, me.id, session.playerToken, transactionId))}
          />
        )}
        {tab === 'banker' && showBankerTab && state.money_mode === 'cash_counter' && (
          <CashCounterPanel
            players={state.players}
            busy={actionBusy}
            error={actionError}
            onAdjust={(playerId, delta) =>
              guarded(() =>
                logTransaction(code, me.id, session.playerToken, {
                  fromPlayerId: delta < 0 ? playerId : null,
                  toPlayerId: delta > 0 ? playerId : null,
                  amount: Math.abs(delta),
                  reason: 'cash count adjustment',
                }),
              )
            }
          />
        )}
        {tab === 'banker' && showBankerTab && showAdvanceRound && (
          <button
            disabled={actionBusy}
            onClick={() => guarded(() => advanceRound(code, me.id, session.playerToken))}
            className="mt-4 w-full rounded-lg border border-amber-700 py-2 text-sm font-medium text-amber-400 hover:bg-amber-950/40 disabled:opacity-50"
          >
            Advance to round {state.round_number + 1} (applies inflation)
          </button>
        )}
        {tab === 'transfer' && showTransferTab && (
          <TransferPanel
            players={state.players}
            myPlayerId={me.id}
            pendingTransfers={state.pending_transfers}
            busy={actionBusy}
            error={actionError}
            onSend={(input) => guarded(() => sendTransfer(code, me.id, session.playerToken, input))}
            onRequest={(input) => guarded(() => requestTransfer(code, me.id, session.playerToken, input))}
            onConfirm={(transactionId) => guarded(() => confirmTransfer(code, me.id, session.playerToken, transactionId))}
            onDecline={(transactionId) => guarded(() => declineTransfer(code, me.id, session.playerToken, transactionId))}
          />
        )}
        {tab === 'land' && state.banker_mode === 'auto' && (
          <LandingPicker
            busy={actionBusy}
            lastOutcome={lastOutcome}
            onDeclare={(spaceIndex, diceRoll) =>
              guarded(async () => {
                const res = await declareLanding(code, session.playerToken, { playerId: me.id, spaceIndex, diceRoll })
                setLastOutcome(res.outcome)
              })
            }
          />
        )}
        {tab === 'draw' && (
          <DrawEventPanel
            eventSystem={state.ruleset.event_system}
            busy={actionBusy}
            lastOutcome={lastDrawOutcome}
            onDraw={(spaceIndex) =>
              guarded(async () => {
                const res = await drawEvent(code, session.playerToken, { playerId: me.id, spaceIndex })
                setLastDrawOutcome(res.outcome)
              })
            }
          />
        )}
        {tab === 'log' && <EventFeed entries={state.recent_log} emptyLabel="No activity yet" />}
        {tab === 'mylog' && <EventFeed entries={myLog} emptyLabel="Nothing has happened to you yet" />}
      </main>

      <nav className="fixed bottom-0 left-0 right-0 mx-auto flex max-w-md overflow-x-auto border-t border-neutral-800 bg-neutral-950">
        <TabButton label="Board" active={tab === 'board'} onClick={() => setTab('board')} />
        {showBankerTab && <TabButton label="Banker" active={tab === 'banker'} onClick={() => setTab('banker')} />}
        {showTransferTab && (
          <TabButton
            label={`Transfer${myPendingRequests > 0 ? ` (${myPendingRequests})` : ''}`}
            active={tab === 'transfer'}
            onClick={() => setTab('transfer')}
          />
        )}
        {state.banker_mode === 'auto' && (
          <TabButton label="I landed…" active={tab === 'land'} onClick={() => setTab('land')} />
        )}
        <TabButton label={state.ruleset.event_system === 'wheel' ? 'Wheel' : 'Cards'} active={tab === 'draw'} onClick={() => setTab('draw')} />
        <TabButton label="Log" active={tab === 'log'} onClick={() => setTab('log')} />
        <TabButton label="My log" active={tab === 'mylog'} onClick={() => setTab('mylog')} />
      </nav>
    </div>
  )
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex-1 whitespace-nowrap px-2 py-3 text-xs font-medium ${active ? 'text-emerald-400' : 'text-neutral-500'}`}>
      {label}
    </button>
  )
}
