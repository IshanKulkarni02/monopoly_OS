import { useParams } from 'react-router-dom'
import { useGameSocket } from '../hooks/useGameSocket'
import { BoardProvider, useFormatMoney } from '../hooks/useBoard'
import { BoardMap } from '../components/BoardMap'
import { PlayerList } from '../components/PlayerList'
import { EventFeed } from '../components/EventFeed'
import type { GameStateOut } from '../api/types'

function DisplayBody({ state, connected }: { state: GameStateOut; connected: boolean }) {
  const formatMoney = useFormatMoney()
  const current = state.players.find((p) => p.id === state.current_turn_player_id)
  const winner = state.players.find((p) => p.id === state.winner_player_id)

  return (
    <div className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 p-8">
      <header className="flex items-center justify-between rounded border-4 border-ink bg-monopoly-red p-6 text-white shadow-[6px_6px_0_#1a1a1a]">
        <div>
          <h1 className="font-display text-4xl tracking-wide">{state.name}</h1>
          <p className="text-lg font-medium text-white/80">Code {state.code} · {connected ? 'Live' : 'Reconnecting…'}</p>
        </div>
        {state.status === 'ended' ? (
          <p className="font-display text-3xl tracking-wide text-monopoly-gold">🏆 {winner?.name ?? '?'} wins!</p>
        ) : current ? (
          <p className="font-display text-3xl tracking-wide">{current.name}'s turn</p>
        ) : null}
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-soft">Standings</h2>
          <PlayerList players={[...state.players].sort((a, b) => b.net_worth - a.net_worth)} />
        </div>
        <div>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wide text-ink-soft">Recent activity</h2>
          <div className="max-h-96 overflow-y-auto rounded border-2 border-ink bg-board-card p-3">
            <EventFeed entries={state.recent_log} emptyLabel="Nothing has happened yet" />
          </div>
        </div>
      </div>

      {state.ruleset.free_parking_pot && state.free_parking_pot_amount > 0 && (
        <p className="text-center text-lg font-bold text-monopoly-gold-dark">
          🎰 Free Parking pot: {formatMoney(state.free_parking_pot_amount)}
        </p>
      )}

      <BoardMap players={state.players} properties={state.properties} defaultCollapsed={false} />
    </div>
  )
}

export function PublicDisplay() {
  const { code = '' } = useParams()
  const { state, connected } = useGameSocket(code)
  if (!state) return <div className="p-10 text-center text-2xl font-bold text-ink-soft">Loading…</div>
  return (
    <BoardProvider tiles={state.board.tiles} groups={state.board.groups} currency={state.ruleset.currency}>
      <DisplayBody state={state} connected={connected} />
    </BoardProvider>
  )
}
