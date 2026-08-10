import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGame, joinGame } from '../api/client'
import { saveSession } from '../hooks/useSession'
import type { EventSystem, MoneyMode, PlayMode } from '../api/types'

const fieldClass =
  'w-full rounded border-2 border-ink bg-board-card p-3 text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red'
const labelClass = 'text-xs font-bold uppercase tracking-wide text-ink-soft'
const primaryButtonClass =
  'rounded border-2 border-ink bg-monopoly-red py-3 font-display text-lg tracking-wide text-white shadow-[3px_3px_0_#1a1a1a] transition hover:bg-monopoly-red-dark hover:shadow-[1px_1px_0_#1a1a1a] disabled:opacity-50 disabled:shadow-none'

export function Landing() {
  const [mode, setMode] = useState<'join' | 'create'>('join')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [gameName, setGameName] = useState('Monopoly Night')
  const [playMode, setPlayMode] = useState<PlayMode>('irl_companion')
  const [bankerMode, setBankerMode] = useState<'manual' | 'auto'>('manual')
  const [moneyMode, setMoneyMode] = useState<MoneyMode>('banker_ledger')
  const [startingCash, setStartingCash] = useState('1500')
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
        startingCash: Number(startingCash) || undefined,
        bankerMode,
        playMode,
        moneyMode,
        eventSystem,
        freeParkingPot,
        challengeBeforeBuy,
        inflationEnabled,
        inflationTrigger,
        inflationRate: (Number(inflationRate) || 0) / 100,
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
          <div>
            <label className={labelClass}>How are you playing?</label>
            <select value={playMode} onChange={(e) => setPlayMode(e.target.value as PlayMode)} className={fieldClass}>
              <option value="irl_companion">Physical board — app just handles banking</option>
              <option value="virtual">Fully virtual — no physical board, app runs the whole game</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Starting cash</label>
              <input type="number" value={startingCash} onChange={(e) => setStartingCash(e.target.value)} className={fieldClass} />
            </div>
            {playMode === 'irl_companion' && (
              <div>
                <label className={labelClass}>Banker mode</label>
                <select value={bankerMode} onChange={(e) => setBankerMode(e.target.value as 'manual' | 'auto')} className={fieldClass}>
                  <option value="manual">Manual (human banker)</option>
                  <option value="auto">Auto (app calculates)</option>
                </select>
              </div>
            )}
          </div>
          <div>
            <label className={labelClass}>Money mode</label>
            <select value={moneyMode} onChange={(e) => setMoneyMode(e.target.value as MoneyMode)} className={fieldClass}>
              <option value="banker_ledger">Banker ledger — banker logs every transaction</option>
              <option value="cash_counter">Cash counter — quick +/- taps, physical cash still moves</option>
              <option value="digital_transfer">Digital transfer — cashless, players pay/request directly</option>
            </select>
          </div>

          <button type="button" onClick={() => setShowTwists(!showTwists)} className="text-left text-sm font-bold text-monopoly-green">
            {showTwists ? '- Hide' : '+ Add'} twists (wheel, challenges, inflation)
          </button>

          {showTwists && (
            <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-3">
              <div>
                <label className={labelClass}>Chance / Community Chest</label>
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
