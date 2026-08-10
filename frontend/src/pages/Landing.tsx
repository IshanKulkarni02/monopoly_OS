import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createGame, joinGame } from '../api/client'
import { saveSession } from '../hooks/useSession'
import type { EventSystem, MoneyMode } from '../api/types'

export function Landing() {
  const [mode, setMode] = useState<'join' | 'create'>('join')
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [gameName, setGameName] = useState('Monopoly Night')
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
      <div className="text-center">
        <h1 className="text-3xl font-bold text-emerald-400">monopoly_OS</h1>
        <p className="mt-1 text-sm text-neutral-400">The banker for your real-life game night.</p>
      </div>

      <div className="flex rounded-xl border border-neutral-800 bg-neutral-900 p-1">
        <button
          onClick={() => setMode('join')}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${mode === 'join' ? 'bg-emerald-700' : 'text-neutral-400'}`}
        >
          Join a game
        </button>
        <button
          onClick={() => setMode('create')}
          className={`flex-1 rounded-lg py-2 text-sm font-medium ${mode === 'create' ? 'bg-emerald-700' : 'text-neutral-400'}`}
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
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-3 text-center font-mono text-xl uppercase tracking-widest"
            maxLength={5}
          />
          <input
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-3"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button disabled={busy || !code || !name} className="rounded-lg bg-emerald-700 py-3 font-medium hover:bg-emerald-600 disabled:opacity-50">
            Join game
          </button>
        </form>
      ) : (
        <form onSubmit={handleCreate} className="flex flex-col gap-3">
          <input
            placeholder="Your name (you'll be host + banker)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-3"
          />
          <input
            placeholder="Game name"
            value={gameName}
            onChange={(e) => setGameName(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-3"
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-neutral-400">Starting cash</label>
              <input
                type="number"
                value={startingCash}
                onChange={(e) => setStartingCash(e.target.value)}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-3"
              />
            </div>
            <div>
              <label className="text-xs text-neutral-400">Banker mode</label>
              <select
                value={bankerMode}
                onChange={(e) => setBankerMode(e.target.value as 'manual' | 'auto')}
                className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-3"
              >
                <option value="manual">Manual (human banker)</option>
                <option value="auto">Auto (app calculates)</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs text-neutral-400">Money mode</label>
            <select
              value={moneyMode}
              onChange={(e) => setMoneyMode(e.target.value as MoneyMode)}
              className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-3"
            >
              <option value="banker_ledger">Banker ledger — banker logs every transaction</option>
              <option value="cash_counter">Cash counter — quick +/- taps, physical cash still moves</option>
              <option value="digital_transfer">Digital transfer — cashless, players pay/request directly</option>
            </select>
          </div>

          <button
            type="button"
            onClick={() => setShowTwists(!showTwists)}
            className="text-left text-sm text-emerald-400"
          >
            {showTwists ? '- Hide' : '+ Add'} twists (wheel, challenges, inflation)
          </button>

          {showTwists && (
            <div className="flex flex-col gap-3 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
              <div>
                <label className="text-xs text-neutral-400">Chance / Community Chest</label>
                <select
                  value={eventSystem}
                  onChange={(e) => setEventSystem(e.target.value as EventSystem)}
                  className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-2"
                >
                  <option value="cards">Classic cards</option>
                  <option value="wheel">Spin the wheel</option>
                </select>
              </div>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={freeParkingPot} onChange={(e) => setFreeParkingPot(e.target.checked)} />
                Free Parking pot (house rule)
              </label>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={challengeBeforeBuy} onChange={(e) => setChallengeBeforeBuy(e.target.checked)} />
                Coin-flip challenge before buying a property
              </label>

              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={inflationEnabled} onChange={(e) => setInflationEnabled(e.target.checked)} />
                Inflation
              </label>
              {inflationEnabled && (
                <div className="grid grid-cols-2 gap-2 pl-6">
                  <select
                    value={inflationTrigger}
                    onChange={(e) => setInflationTrigger(e.target.value as 'on_pass_go' | 'per_round')}
                    className="rounded-lg border border-neutral-700 bg-neutral-950 p-2 text-sm"
                  >
                    <option value="on_pass_go">Each time anyone passes GO</option>
                    <option value="per_round">Each round (banker advances)</option>
                  </select>
                  <input
                    type="number"
                    value={inflationRate}
                    onChange={(e) => setInflationRate(e.target.value)}
                    placeholder="Rate %"
                    className="rounded-lg border border-neutral-700 bg-neutral-950 p-2 text-sm"
                  />
                </div>
              )}
            </div>
          )}

          {error && <p className="text-sm text-red-400">{error}</p>}
          <button disabled={busy || !name} className="rounded-lg bg-emerald-700 py-3 font-medium hover:bg-emerald-600 disabled:opacity-50">
            Create game
          </button>
        </form>
      )}
    </div>
  )
}
