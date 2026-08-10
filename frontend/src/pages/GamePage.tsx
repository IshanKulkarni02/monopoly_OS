import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useGameSocket } from '../hooks/useGameSocket'
import { useSession } from '../hooks/useSession'
import { JoinCodeBadge } from '../components/JoinCodeBadge'
import { PlayerList } from '../components/PlayerList'
import { PropertyBoard } from '../components/PropertyBoard'
import { BankerPanel } from '../components/BankerPanel'
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
  getPlayerLog,
} from '../api/client'
import type { EventLogOut, LandOutcome } from '../api/types'

type Tab = 'board' | 'banker' | 'land' | 'log' | 'mylog'

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
  const [lastOutcome, setLastOutcome] = useState<LandOutcome | null>(null)
  const [myLog, setMyLog] = useState<EventLogOut[]>([])

  useEffect(() => {
    if (tab === 'mylog' && session && state) {
      getPlayerLog(code, session.playerId)
        .then((log) => setMyLog(log as EventLogOut[]))
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

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col pb-20">
      <header className="flex items-center justify-between border-b border-neutral-800 p-4">
        <div>
          <h1 className="font-bold">{state.name}</h1>
          <p className="text-xs text-neutral-500">
            Code {state.code} · {connected ? 'Live' : 'Reconnecting…'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-neutral-500">Your balance</p>
          <p className="font-mono text-xl text-emerald-400">{formatMoney(me.balance)}</p>
        </div>
      </header>

      <main className="flex-1 p-4">
        {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}
        {tab === 'board' && (
          <PropertyBoard
            properties={state.properties}
            players={state.players}
            myPlayerId={me.id}
            onPurchase={(propertyId) => guarded(() => purchaseProperty(code, me.id, session.playerToken, propertyId))}
          />
        )}
        {tab === 'banker' && me.is_banker && (
          <BankerPanel
            players={state.players}
            recentLog={state.recent_log}
            busy={actionBusy}
            error={actionError}
            onLogTransaction={(input) => guarded(() => logTransaction(code, me.id, session.playerToken, input))}
            onReverse={(transactionId) => guarded(() => reverseTransaction(code, me.id, session.playerToken, transactionId))}
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
        {tab === 'log' && <EventFeed entries={state.recent_log} emptyLabel="No activity yet" />}
        {tab === 'mylog' && <EventFeed entries={myLog} emptyLabel="Nothing has happened to you yet" />}
      </main>

      <nav className="fixed bottom-0 left-0 right-0 mx-auto flex max-w-md border-t border-neutral-800 bg-neutral-950">
        <TabButton label="Board" active={tab === 'board'} onClick={() => setTab('board')} />
        {me.is_banker && <TabButton label="Banker" active={tab === 'banker'} onClick={() => setTab('banker')} />}
        {state.banker_mode === 'auto' && (
          <TabButton label="I landed…" active={tab === 'land'} onClick={() => setTab('land')} />
        )}
        <TabButton label="Log" active={tab === 'log'} onClick={() => setTab('log')} />
        <TabButton label="My log" active={tab === 'mylog'} onClick={() => setTab('mylog')} />
      </nav>
    </div>
  )
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex-1 py-3 text-xs font-medium ${active ? 'text-emerald-400' : 'text-neutral-500'}`}>
      {label}
    </button>
  )
}
