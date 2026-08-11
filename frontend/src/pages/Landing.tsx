import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGame, duplicateBoard, joinGame, listBoards, login, signup } from '../api/client'
import { saveSession } from '../hooks/useSession'
import { useAccount } from '../hooks/useAccount'
import type { BoardSummaryOut, EventSystem, MoneyMode, PlayMode } from '../api/types'

const fieldClass =
  'w-full rounded border-2 border-ink bg-board-card p-3 text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red'
const labelClass = 'text-xs font-bold uppercase tracking-wide text-ink-soft'
const primaryButtonClass =
  'rounded border-2 border-ink bg-monopoly-red py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-red-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none'

function AccountBar() {
  const { account, saveAccount, logout } = useAccount()
  const [open, setOpen] = useState(false)
  const [authMode, setAuthMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (account) {
    return (
      <div className="flex items-center justify-between rounded border-2 border-ink bg-board-card px-3 py-2 text-sm">
        <span className="font-bold text-ink">Signed in as {account.user.name}</span>
        <button onClick={logout} className="text-xs font-bold text-monopoly-red hover:underline">
          Sign out
        </button>
      </div>
    )
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = authMode === 'login' ? await login(email.trim(), password) : await signup(email.trim(), password, displayName.trim())
      saveAccount({ user: res.user, sessionToken: res.session_token })
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded border-2 border-ink bg-board-card px-3 py-2 text-center text-sm font-bold text-ink-soft hover:bg-board"
      >
        Sign in — optional, lets you save custom boards
      </button>
    )
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
      <div className="flex gap-1 rounded border-2 border-ink p-1">
        <button
          type="button"
          onClick={() => setAuthMode('login')}
          className={`flex-1 rounded py-1 text-xs font-bold uppercase ${authMode === 'login' ? 'bg-monopoly-green text-white' : 'text-ink-soft'}`}
        >
          Sign in
        </button>
        <button
          type="button"
          onClick={() => setAuthMode('signup')}
          className={`flex-1 rounded py-1 text-xs font-bold uppercase ${authMode === 'signup' ? 'bg-monopoly-green text-white' : 'text-ink-soft'}`}
        >
          Create account
        </button>
      </div>
      {authMode === 'signup' && (
        <input placeholder="Your name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} className={`${fieldClass} p-2 text-sm`} />
      )}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} className={`${fieldClass} p-2 text-sm`} />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className={`${fieldClass} p-2 text-sm`}
      />
      {error && <p className="text-xs font-semibold text-monopoly-red">{error}</p>}
      <div className="flex gap-2">
        <button disabled={busy || !email || !password} className="flex-1 rounded border-2 border-ink bg-monopoly-green py-2 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50">
          {authMode === 'login' ? 'Sign in' : 'Create account'}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="rounded border-2 border-ink px-3 text-sm font-bold text-ink-soft hover:bg-board">
          Cancel
        </button>
      </div>
    </form>
  )
}

export function Landing() {
  const { account } = useAccount()
  const [mode, setMode] = useState<'join' | 'create'>('join')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [gameName, setGameName] = useState('Monopoly Night')
  const [boards, setBoards] = useState<BoardSummaryOut[]>([])
  const [boardKey, setBoardKey] = useState('')
  const [playMode, setPlayMode] = useState<PlayMode>('irl_companion')
  const [bankerMode, setBankerMode] = useState<'manual' | 'auto'>('auto')
  const [cashType, setCashType] = useState<'cash' | 'upi'>('cash')
  const [moneyMode, setMoneyMode] = useState<MoneyMode>('banker_ledger')
  const [diceCount, setDiceCount] = useState('2')
  const [turnOrderMode, setTurnOrderMode] = useState<'highest_roll_first' | 'entry_order'>('highest_roll_first')
  const [startingCash, setStartingCash] = useState('')
  const [showTwists, setShowTwists] = useState(false)
  const [eventSystem, setEventSystem] = useState<EventSystem>('cards')
  const [freeParkingPot, setFreeParkingPot] = useState(false)
  const [challengeBeforeBuy, setChallengeBeforeBuy] = useState(false)
  const [inflationEnabled, setInflationEnabled] = useState(false)
  const [inflationTrigger, setInflationTrigger] = useState<'on_pass_go' | 'per_round'>('on_pass_go')
  const [inflationRate, setInflationRate] = useState('5')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    listBoards(account?.sessionToken)
      .then((list) => {
        setBoards(list)
        const preferred = list.find((b) => b.key === 'current_game') ?? list[0]
        if (preferred) setBoardKey(preferred.key)
      })
      .catch(() => {})
  }, [account?.sessionToken])

  const isIrlTracked = playMode === 'irl_companion' && bankerMode === 'auto'
  const selectedBoard = boards.find((b) => b.key === boardKey)
  const ownsSelectedBoard = Boolean(account && selectedBoard?.owner_user_id === account.user.id)

  async function handleEditOrDuplicateBoard() {
    if (!account || !selectedBoard) return
    if (ownsSelectedBoard) {
      navigate(`/boards/${selectedBoard.key}/edit`)
      return
    }
    const name = window.prompt('Name your customized copy:', `${selectedBoard.name} (mine)`)
    if (!name) return
    const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
    const key = slug || `board-${Date.now()}`
    try {
      const created = await duplicateBoard(selectedBoard.key, account.sessionToken, {
        key,
        name,
        description: `Customized from ${selectedBoard.name}`,
      })
      navigate(`/boards/${created.key}/edit`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not duplicate board')
    }
  }

  async function handleJoin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = await joinGame(code.trim().toUpperCase(), name.trim())
      saveSession({
        code: res.game.code,
        playerId: res.player_id,
        playerToken: res.player_token,
        playerName: name.trim(),
      })
      navigate(`/g/${res.game.code}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not join game')
    } finally {
      setBusy(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = await createGame({
        hostName: name.trim(),
        name: gameName.trim(),
        boardKey: boardKey || undefined,
        startingCash: Number(startingCash) || undefined,
        bankerMode,
        playMode,
        moneyMode: playMode === 'irl_companion' ? (cashType === 'upi' ? 'digital_transfer' : moneyMode) : moneyMode,
        eventSystem,
        freeParkingPot,
        challengeBeforeBuy,
        inflationEnabled,
        inflationTrigger,
        inflationRate: (Number(inflationRate) || 0) / 100,
        diceCount: Number(diceCount) || 2,
        turnOrderMode,
        sessionToken: account?.sessionToken,
      })
      saveSession({
        code: res.game.code,
        playerId: res.host_player_id,
        playerToken: res.player_token,
        hostToken: res.host_token,
        playerName: name.trim(),
      })
      navigate(`/g/${res.game.code}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create game')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <div className="rounded border-4 border-ink bg-monopoly-red p-5 text-center shadow-[6px_6px_0_#1a1a1a]">
        <h1 className="font-display text-4xl tracking-wide text-white drop-shadow-[2px_2px_0_rgba(0,0,0,0.3)]">MONOPOLY_OS</h1>
        <p className="mt-1 text-sm font-medium text-white/90">The banker for your real-life game night.</p>
      </div>

      <AccountBar />

      <div className="flex gap-2 rounded border-2 border-ink bg-board-card p-1">
        <button
          onClick={() => setMode('join')}
          className={`flex-1 rounded py-2 text-sm font-bold uppercase tracking-wide ${
            mode === 'join' ? 'bg-monopoly-green text-white' : 'text-ink-soft'
          }`}
        >
          Join a game
        </button>
        <button
          onClick={() => setMode('create')}
          className={`flex-1 rounded py-2 text-sm font-bold uppercase tracking-wide ${
            mode === 'create' ? 'bg-monopoly-green text-white' : 'text-ink-soft'
          }`}
        >
          Host a game
        </button>
      </div>

      {mode === 'join' ? (
        <form onSubmit={handleJoin} className="flex flex-col gap-3">
          <input
            placeholder="Join code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className={`${fieldClass} text-center font-mono text-xl uppercase tracking-widest`}
            maxLength={5}
          />
          <input placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
          {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
          <button disabled={busy || !code || !name} className={primaryButtonClass}>
            Join game
          </button>
          <p className="text-center text-xs font-medium text-ink-soft">
            Playing in person? The host can also add you by name from their screen — no need to join yourself.
          </p>
        </form>
      ) : (
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <input
            placeholder="Your name (you'll be host + banker)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={fieldClass}
          />
          <input placeholder="Game name" value={gameName} onChange={(e) => setGameName(e.target.value)} className={fieldClass} />
          {boards.length > 0 && (
            <div>
              <label className={labelClass}>Board</label>
              <select value={boardKey} onChange={(e) => setBoardKey(e.target.value)} className={fieldClass}>
                {boards.map((b) => (
                  <option key={b.key} value={b.key}>
                    {b.name}
                    {b.owner_user_id ? ' (yours)' : ''}
                  </option>
                ))}
              </select>
              {selectedBoard?.description && <p className="mt-1 text-xs font-medium text-ink-soft">{selectedBoard.description}</p>}
              {account && (
                <button type="button" onClick={handleEditOrDuplicateBoard} className="mt-1 text-xs font-bold text-monopoly-green hover:underline">
                  {ownsSelectedBoard ? '✎ Edit this board' : '⎘ Duplicate & customize this board'}
                </button>
              )}
            </div>
          )}
          <div>
            <label className={labelClass}>How are you playing?</label>
            <select value={playMode} onChange={(e) => setPlayMode(e.target.value as PlayMode)} className={fieldClass}>
              <option value="irl_companion">Physical board — everyone plays in the room</option>
              <option value="virtual">Fully virtual — no physical board, app runs the whole game</option>
            </select>
          </div>

          {playMode === 'irl_companion' ? (
            <>
              <div>
                <label className={labelClass}>Banking style</label>
                <select value={bankerMode} onChange={(e) => setBankerMode(e.target.value as 'manual' | 'auto')} className={fieldClass}>
                  <option value="auto">Auto — app tracks positions and does the math (recommended)</option>
                  <option value="manual">Manual — a human banker logs everything by hand</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>How does money move?</label>
                <div className="flex gap-2 rounded border-2 border-ink p-1">
                  <button
                    type="button"
                    onClick={() => setCashType('cash')}
                    className={`flex-1 rounded py-2 text-sm font-bold ${cashType === 'cash' ? 'bg-monopoly-green text-white' : 'text-ink-soft'}`}
                  >
                    💵 Cash
                  </button>
                  <button
                    type="button"
                    onClick={() => setCashType('upi')}
                    className={`flex-1 rounded py-2 text-sm font-bold ${cashType === 'upi' ? 'bg-monopoly-green text-white' : 'text-ink-soft'}`}
                  >
                    📱 UPI
                  </button>
                </div>
                <p className="mt-1 text-xs font-medium text-ink-soft">
                  {cashType === 'upi'
                    ? 'Players connect their own phone to send/request money themselves.'
                    : "Physical cash on the table — players can skip connecting a phone; you can run their turns from your screen."}
                </p>
              </div>
              {cashType === 'cash' && (
                <label className="flex items-center gap-2 text-xs font-medium text-ink-soft">
                  <input
                    type="checkbox"
                    checked={moneyMode === 'cash_counter'}
                    onChange={(e) => setMoneyMode(e.target.checked ? 'cash_counter' : 'banker_ledger')}
                  />
                  Quick +/- taps instead of from/to transaction entries
                </label>
              )}
            </>
          ) : (
            <div>
              <label className={labelClass}>Money mode</label>
              <select value={moneyMode} onChange={(e) => setMoneyMode(e.target.value as MoneyMode)} className={fieldClass}>
                <option value="banker_ledger">Banker ledger</option>
                <option value="cash_counter">Cash counter</option>
                <option value="digital_transfer">Digital transfer</option>
              </select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Starting cash</label>
              <input
                type="number"
                placeholder="Board default"
                value={startingCash}
                onChange={(e) => setStartingCash(e.target.value)}
                className={fieldClass}
              />
            </div>
            {isIrlTracked && (
              <div>
                <label className={labelClass}>Dice</label>
                <select value={diceCount} onChange={(e) => setDiceCount(e.target.value)} className={fieldClass}>
                  <option value="1">1 die</option>
                  <option value="2">2 dice</option>
                </select>
              </div>
            )}
          </div>

          {isIrlTracked && (
            <div>
              <label className={labelClass}>Turn order</label>
              <select value={turnOrderMode} onChange={(e) => setTurnOrderMode(e.target.value as 'highest_roll_first' | 'entry_order')} className={fieldClass}>
                <option value="highest_roll_first">Everyone rolls, highest goes first</option>
                <option value="entry_order">Whoever's entered first goes first</option>
              </select>
            </div>
          )}

          <button type="button" onClick={() => setShowTwists(!showTwists)} className="text-left text-sm font-bold text-monopoly-green">
            {showTwists ? '- Hide' : '+ Add'} twists (wheel, challenges, inflation)
          </button>

          {showTwists && (
            <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-3">
              <div>
                <label className={labelClass}>Mystery draws</label>
                <select value={eventSystem} onChange={(e) => setEventSystem(e.target.value as EventSystem)} className={fieldClass}>
                  <option value="cards">Classic cards</option>
                  <option value="wheel">Spin the wheel</option>
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={freeParkingPot} onChange={(e) => setFreeParkingPot(e.target.checked)} />
                Free Parking pot (house rule)
              </label>

              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={challengeBeforeBuy} onChange={(e) => setChallengeBeforeBuy(e.target.checked)} />
                Coin-flip challenge before buying a property
              </label>

              <label className="flex items-center gap-2 text-sm font-medium">
                <input type="checkbox" checked={inflationEnabled} onChange={(e) => setInflationEnabled(e.target.checked)} />
                Inflation
              </label>
              {inflationEnabled && (
                <div className="grid grid-cols-2 gap-2 pl-6">
                  <select
                    value={inflationTrigger}
                    onChange={(e) => setInflationTrigger(e.target.value as 'on_pass_go' | 'per_round')}
                    className={`${fieldClass} p-2 text-sm`}
                  >
                    <option value="on_pass_go">Each time anyone passes GO</option>
                    <option value="per_round">Each round (banker advances)</option>
                  </select>
                  <input
                    type="number"
                    value={inflationRate}
                    onChange={(e) => setInflationRate(e.target.value)}
                    placeholder="Rate %"
                    className={`${fieldClass} p-2 text-sm`}
                  />
                </div>
              )}
            </div>
          )}

          {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
          <button disabled={busy || !name} className={primaryButtonClass}>
            Create game
          </button>
        </form>
      )}
    </div>
  )
}
