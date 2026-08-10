import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useGameSocket } from '../hooks/useGameSocket'
import { useSession } from '../hooks/useSession'
import { useAccount } from '../hooks/useAccount'
import { JoinCodeBadge } from '../components/JoinCodeBadge'
import { PlayerList } from '../components/PlayerList'
import { PropertyBoard } from '../components/PropertyBoard'
import { BankerPanel } from '../components/BankerPanel'
import { CashCounterPanel } from '../components/CashCounterPanel'
import { TransferPanel } from '../components/TransferPanel'
import { DrawEventPanel } from '../components/DrawEventPanel'
import { LandingPicker } from '../components/LandingPicker'
import { VirtualPlayPanel } from '../components/VirtualPlayPanel'
import { IrlLivePanel } from '../components/IrlLivePanel'
import { EventFeed } from '../components/EventFeed'
import { formatMoney } from '../boardData'
import { BoardProvider } from '../hooks/useBoard'
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
  rollDice,
  endTurn,
  buildHouse,
  sellHouse,
  mortgageProperty,
  unmortgageProperty,
  addBot,
  addPlayer,
  getPlayerLog,
  saveBoardTemplate,
} from '../api/client'
import type { DrawEventOutcome, EventLogOut, LandOutcome, RollOutcome } from '../api/types'

type Tab = 'board' | 'banker' | 'transfer' | 'land' | 'draw' | 'play' | 'log' | 'mylog'

export function GamePage() {
  const { code = '' } = useParams()
  const { session, saveSession: persistSession } = useSession(code)
  const { state, connected } = useGameSocket(code)
  const { account } = useAccount()
  const [tab, setTab] = useState<Tab>('board')
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateKey, setTemplateKey] = useState('')
  const [templateName, setTemplateName] = useState('')
  const [templateSaved, setTemplateSaved] = useState<string | null>(null)
  const [joinName, setJoinName] = useState('')
  const [joinError, setJoinError] = useState<string | null>(null)
  const [joinBusy, setJoinBusy] = useState(false)
  const [addPlayerName, setAddPlayerName] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [purchaseMessage, setPurchaseMessage] = useState<string | null>(null)
  const [lastOutcome, setLastOutcome] = useState<LandOutcome | null>(null)
  const [lastDrawOutcome, setLastDrawOutcome] = useState<DrawEventOutcome | null>(null)
  const [lastRoll, setLastRoll] = useState<RollOutcome | null>(null)
  const [myLog, setMyLog] = useState<EventLogOut[]>([])
  const [initialTabSet, setInitialTabSet] = useState(false)

  useEffect(() => {
    if (tab === 'mylog' && session && state) {
      getPlayerLog(code, session.playerId)
        .then((log) => setMyLog(log))
        .catch(() => {})
    }
  }, [tab, session, code, state])

  useEffect(() => {
    if (!initialTabSet && state?.status === 'active') {
      setTab(state.play_mode === 'virtual' || state.banker_mode === 'auto' ? 'play' : 'board')
      setInitialTabSet(true)
    }
  }, [state, initialTabSet])

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
        <h1 className="text-center font-display text-3xl tracking-wide text-monopoly-red">{state.name}</h1>
        <p className="text-center text-sm font-semibold text-ink-soft">Join code {code}</p>
        <form onSubmit={handleJoin} className="flex flex-col gap-3">
          <input
            placeholder="Your name"
            value={joinName}
            onChange={(e) => setJoinName(e.target.value)}
            className="w-full rounded border-2 border-ink bg-board-card p-3 text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
          />
          {joinError && <p className="text-sm font-semibold text-monopoly-red">{joinError}</p>}
          <button
            disabled={joinBusy || !joinName}
            className="rounded border-2 border-ink bg-monopoly-red py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-red-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none"
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
        <h1 className="text-center font-display text-2xl tracking-wide text-monopoly-red">{state.name}</h1>
        <JoinCodeBadge code={state.code} />
        <div>
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Players ({state.players.length})</h2>
          <PlayerList
            players={state.players}
            myPlayerId={me.id}
            canManageBanker={me.is_host}
            onToggleBanker={(playerId, next) => guarded(() => setBanker(code, session.hostToken!, playerId, next))}
          />
        </div>
        {me.is_host && (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const trimmed = addPlayerName.trim()
              if (!trimmed) return
              guarded(() => addPlayer(code, session.hostToken!, trimmed)).then(() => setAddPlayerName(''))
            }}
            className="flex gap-2"
          >
            <input
              placeholder="Add a player by name"
              value={addPlayerName}
              onChange={(e) => setAddPlayerName(e.target.value)}
              className="w-full rounded border-2 border-ink bg-board-card p-2 text-sm text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
            />
            <button
              disabled={actionBusy || !addPlayerName.trim()}
              className="whitespace-nowrap rounded border-2 border-ink bg-board-card px-3 text-sm font-bold text-ink hover:bg-board disabled:opacity-50"
            >
              Add
            </button>
          </form>
        )}
        {me.is_host && state.play_mode === 'virtual' && (
          <button
            disabled={actionBusy}
            onClick={() => guarded(() => addBot(code, session.hostToken!))}
            className="rounded border-2 border-ink bg-board-card py-2 text-sm font-bold text-ink hover:bg-board disabled:opacity-50"
          >
            🤖 Add a bot player
          </button>
        )}
        {me.is_host && (
          <button
            disabled={actionBusy || state.players.length < 2}
            onClick={() => guarded(() => startGame(code, session.hostToken!))}
            className="rounded border-2 border-ink bg-monopoly-green py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-green-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none"
          >
            {state.players.length < 2 ? 'Need at least 2 players' : 'Start game'}
          </button>
        )}
        {actionError && <p className="text-center text-sm font-semibold text-monopoly-red">{actionError}</p>}
        {!connected && <p className="text-center text-xs font-semibold text-monopoly-gold-dark">Reconnecting…</p>}
      </div>
    )
  }

  const myPendingRequests = state.pending_transfers.filter((t) => t.from_player_id === me.id).length
  const isVirtual = state.play_mode === 'virtual'
  const showIrlLiveTab = !isVirtual && state.banker_mode === 'auto'
  const showBankerTab = me.is_banker && (state.money_mode === 'banker_ledger' || state.money_mode === 'cash_counter')
  const showTransferTab = state.money_mode === 'digital_transfer'
  const showLandTab = !isVirtual && state.banker_mode === 'auto'
  const showAdvanceRound = me.is_banker && state.ruleset.inflation.enabled && state.ruleset.inflation.trigger === 'per_round'

  return (
    <BoardProvider tiles={state.board.tiles} groups={state.board.groups} currency={state.ruleset.currency}>
    <div className="mx-auto flex min-h-screen max-w-md flex-col pb-20">
      <header className="flex items-center justify-between border-b-4 border-ink bg-monopoly-red p-4 text-white">
        <div>
          <h1 className="font-display text-lg tracking-wide">{state.name}</h1>
          <p className="text-xs font-medium text-white/80">
            Code {state.code} · {connected ? 'Live' : 'Reconnecting…'}
          </p>
          {state.ruleset.inflation.enabled && (
            <p className="text-xs font-bold text-monopoly-gold">
              Inflation {state.inflation_multiplier.toFixed(2)}x · Round {state.round_number}
            </p>
          )}
        </div>
        <div className="text-right">
          <p className="text-xs font-medium text-white/80">Your balance</p>
          <p className="font-mono text-xl font-bold text-white">{formatMoney(me.balance, state.ruleset.currency.symbol)}</p>
          {me.jail_free_cards > 0 && <p className="text-xs font-medium text-white/80">{me.jail_free_cards}x jail-free card</p>}
        </div>
      </header>

      <main className="flex-1 p-4">
        {actionError && <p className="mb-3 text-sm font-semibold text-monopoly-red">{actionError}</p>}
        {tab === 'play' && isVirtual && (
          <VirtualPlayPanel
            players={state.players}
            properties={state.properties}
            myPlayerId={me.id}
            currentTurnPlayerId={state.current_turn_player_id}
            busy={actionBusy}
            error={actionError}
            lastRoll={lastRoll}
            onRoll={(opts) =>
              guarded(async () => {
                const res = await rollDice(code, me.id, session.playerToken, opts)
                setLastRoll(res.result)
              })
            }
            onEndTurn={() => guarded(() => endTurn(code, me.id, session.playerToken))}
            onPurchase={handlePurchase}
          />
        )}
        {tab === 'play' && showIrlLiveTab && (
          <IrlLivePanel
            code={code}
            state={state}
            myPlayerId={me.id}
            hostToken={session.hostToken}
            playerToken={session.playerToken}
            isHost={me.is_host}
          />
        )}
        {tab === 'board' && (
          <>
            {me.is_host && account && (
              <div className="mb-3 rounded border-2 border-ink bg-board-card p-3">
                {!showSaveTemplate ? (
                  <button
                    onClick={() => setShowSaveTemplate(true)}
                    className="text-sm font-bold text-monopoly-green hover:underline"
                  >
                    + Save this board as a reusable template
                  </button>
                ) : (
                  <div className="flex flex-col gap-2">
                    <input
                      placeholder="Template key (e.g. friday-night)"
                      value={templateKey}
                      onChange={(e) => setTemplateKey(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '-'))}
                      className="rounded border-2 border-ink bg-board p-2 text-sm text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
                    />
                    <input
                      placeholder="Display name"
                      value={templateName}
                      onChange={(e) => setTemplateName(e.target.value)}
                      className="rounded border-2 border-ink bg-board p-2 text-sm text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red"
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={actionBusy || !templateKey || !templateName}
                        onClick={() =>
                          guarded(async () => {
                            await saveBoardTemplate(code, session.hostToken!, account.sessionToken, {
                              key: templateKey,
                              name: templateName,
                              description: `Saved from ${state.name}`,
                            })
                            setTemplateSaved(templateName)
                            setShowSaveTemplate(false)
                          })
                        }
                        className="rounded border-2 border-ink bg-monopoly-green px-3 py-1.5 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
                      >
                        Save
                      </button>
                      <button onClick={() => setShowSaveTemplate(false)} className="rounded border-2 border-ink px-3 py-1.5 text-sm font-bold text-ink-soft hover:bg-board">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
                {templateSaved && <p className="mt-1 text-xs font-semibold text-monopoly-green">Saved "{templateSaved}" — pick it next time you host.</p>}
              </div>
            )}
            {purchaseMessage && <p className="mb-3 text-sm font-semibold text-ink">{purchaseMessage}</p>}
            <PropertyBoard
              properties={state.properties}
              players={state.players}
              myPlayerId={me.id}
              onPurchase={handlePurchase}
              mortgagePercentage={state.ruleset.mortgage_percentage}
              mortgageInterest={state.ruleset.mortgage_interest}
              onBuildHouse={(propertyId) => guarded(() => buildHouse(code, me.id, session.playerToken, propertyId))}
              onSellHouse={(propertyId) => guarded(() => sellHouse(code, me.id, session.playerToken, propertyId))}
              onMortgage={(propertyId) => guarded(() => mortgageProperty(code, me.id, session.playerToken, propertyId))}
              onUnmortgage={(propertyId) => guarded(() => unmortgageProperty(code, me.id, session.playerToken, propertyId))}
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
            className="mt-4 w-full rounded border-2 border-ink bg-monopoly-gold py-2 text-sm font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50"
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
        {tab === 'land' && showLandTab && (
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
        {tab === 'draw' && !isVirtual && (
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

      <nav className="fixed bottom-0 left-0 right-0 mx-auto flex max-w-md overflow-x-auto border-t-4 border-ink bg-board-card">
        {(isVirtual || showIrlLiveTab) && <TabButton label="Play" active={tab === 'play'} onClick={() => setTab('play')} />}
        <TabButton label="Board" active={tab === 'board'} onClick={() => setTab('board')} />
        {showBankerTab && <TabButton label="Banker" active={tab === 'banker'} onClick={() => setTab('banker')} />}
        {showTransferTab && (
          <TabButton
            label={`Transfer${myPendingRequests > 0 ? ` (${myPendingRequests})` : ''}`}
            active={tab === 'transfer'}
            onClick={() => setTab('transfer')}
          />
        )}
        {showLandTab && <TabButton label="I landed…" active={tab === 'land'} onClick={() => setTab('land')} />}
        {!isVirtual && (
          <TabButton label={state.ruleset.event_system === 'wheel' ? 'Wheel' : 'Cards'} active={tab === 'draw'} onClick={() => setTab('draw')} />
        )}
        <TabButton label="Log" active={tab === 'log'} onClick={() => setTab('log')} />
        <TabButton label="My log" active={tab === 'mylog'} onClick={() => setTab('mylog')} />
      </nav>
    </div>
    </BoardProvider>
  )
}

function TabButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 whitespace-nowrap border-t-4 px-2 py-3 text-xs font-bold uppercase tracking-wide ${
        active ? 'border-monopoly-red text-monopoly-red' : 'border-transparent text-ink-soft'
      }`}
    >
      {label}
    </button>
  )
}
