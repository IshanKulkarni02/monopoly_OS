import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listBoards, runSimulation, compareSimulations, getLandingProbabilities } from '../api/client'
import type { BoardSummaryOut, LandingProbabilityTile, SimulationAggregate, SimulationCompareResult } from '../api/types'

const fieldClass = 'w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red'
const labelClass = 'text-xs font-bold uppercase tracking-wide text-ink-soft'

function parseOverrides(text: string): Record<string, unknown> {
  if (!text.trim()) return {}
  return JSON.parse(text)
}

function AggregateSummary({ agg, title }: { agg: SimulationAggregate; title?: string }) {
  return (
    <div className="rounded border-2 border-ink bg-board-card p-3">
      {title && <p className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">{title}</p>}
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>Games played: <b>{agg.games_played}</b></div>
        <div>Hit turn cap: <b>{agg.games_hit_turn_cap}</b></div>
        <div>Avg turns: <b>{agg.average_turns_played}</b></div>
        <div>Avg final net worth: <b>{agg.average_final_net_worth}</b></div>
        <div>Avg bankruptcies: <b>{agg.average_bankruptcies_per_game}</b></div>
        <div>Avg auctions: <b>{agg.average_auctions_per_game}</b></div>
        <div>Avg trades: <b>{agg.average_trades_per_game}</b></div>
        <div>Avg houses built: <b>{agg.average_houses_built_per_game}</b></div>
      </div>
      <p className="mt-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Win rate by starting position</p>
      <div className="flex flex-wrap gap-2 text-sm">
        {Object.entries(agg.win_rate_by_starting_position).map(([idx, rate]) => (
          <span key={idx} className="rounded border border-ink bg-board px-2 py-0.5">
            #{Number(idx) + 1}: {(rate * 100).toFixed(0)}%
          </span>
        ))}
      </div>
    </div>
  )
}

export function EconomyLab() {
  const [boards, setBoards] = useState<BoardSummaryOut[]>([])
  const [boardKey, setBoardKey] = useState('')
  const [numGames, setNumGames] = useState('10')
  const [numBots, setNumBots] = useState('4')
  const [maxTurns, setMaxTurns] = useState('500')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [result, setResult] = useState<SimulationAggregate | null>(null)

  const [compareMode, setCompareMode] = useState(false)
  const [baselineJson, setBaselineJson] = useState('{}')
  const [variantJson, setVariantJson] = useState('{\n  "starting_cash": 3000\n}')
  const [compareResult, setCompareResult] = useState<SimulationCompareResult | null>(null)

  const [diceCount, setDiceCount] = useState('2')
  const [probTiles, setProbTiles] = useState<LandingProbabilityTile[] | null>(null)

  useEffect(() => {
    listBoards().then((bs) => {
      setBoards(bs)
      if (bs.length > 0) setBoardKey(bs[0].key)
    }).catch(() => {})
  }, [])

  async function handleRunSimulation() {
    if (!boardKey) return
    setError(null)
    setBusy(true)
    setResult(null)
    setCompareResult(null)
    try {
      if (compareMode) {
        const res = await compareSimulations({
          boardKey,
          baselineOverrides: parseOverrides(baselineJson),
          variantOverrides: parseOverrides(variantJson),
          numGames: Number(numGames) || 10,
          numBots: Number(numBots) || 4,
          maxTurns: Number(maxTurns) || 500,
        })
        setCompareResult(res)
      } else {
        const res = await runSimulation({
          boardKey,
          numGames: Number(numGames) || 10,
          numBots: Number(numBots) || 4,
          maxTurns: Number(maxTurns) || 500,
        })
        setResult(res)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed')
    } finally {
      setBusy(false)
    }
  }

  async function handleShowProbabilities() {
    if (!boardKey) return
    setError(null)
    setBusy(true)
    try {
      const res = await getLandingProbabilities(boardKey, Number(diceCount) || 2)
      setProbTiles(res.tiles)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not compute probabilities')
    } finally {
      setBusy(false)
    }
  }

  const maxProb = probTiles ? Math.max(...probTiles.map((t) => t.probability)) : 1

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-6">
      <div className="rounded border-4 border-ink bg-monopoly-red p-5 text-center shadow-[6px_6px_0_#1a1a1a]">
        <h1 className="font-display text-3xl tracking-wide text-white">🧪 Economy Lab</h1>
        <p className="mt-1 text-sm font-medium text-white/90">
          Simulate all-bot games to see how a board or ruleset actually plays out before handing it to real people.
        </p>
      </div>
      <Link to="/" className="text-sm font-bold text-monopoly-green hover:underline">← Back home</Link>

      <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-4">
        <div>
          <label className={labelClass}>Board</label>
          <select value={boardKey} onChange={(e) => setBoardKey(e.target.value)} className={fieldClass}>
            {boards.map((b) => (
              <option key={b.key} value={b.key}>{b.name}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className={labelClass}>Games</label>
            <input type="number" min={1} max={50} value={numGames} onChange={(e) => setNumGames(e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Bots</label>
            <input type="number" min={2} max={6} value={numBots} onChange={(e) => setNumBots(e.target.value)} className={fieldClass} />
          </div>
          <div>
            <label className={labelClass}>Max turns/game</label>
            <input type="number" min={50} max={1000} value={maxTurns} onChange={(e) => setMaxTurns(e.target.value)} className={fieldClass} />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm font-medium">
          <input type="checkbox" checked={compareMode} onChange={(e) => setCompareMode(e.target.checked)} />
          Compare two ruleset configs (baseline vs. variant)
        </label>
        {compareMode && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelClass}>Baseline overrides (JSON)</label>
              <textarea value={baselineJson} onChange={(e) => setBaselineJson(e.target.value)} rows={4} className={`${fieldClass} font-mono text-xs`} />
            </div>
            <div>
              <label className={labelClass}>Variant overrides (JSON)</label>
              <textarea value={variantJson} onChange={(e) => setVariantJson(e.target.value)} rows={4} className={`${fieldClass} font-mono text-xs`} />
            </div>
          </div>
        )}

        {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
        <button
          disabled={busy || !boardKey}
          onClick={handleRunSimulation}
          className="rounded border-2 border-ink bg-monopoly-green py-2 font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
        >
          {busy ? 'Running…' : 'Run simulation'}
        </button>
      </div>

      {result && <AggregateSummary agg={result} />}
      {compareResult && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <AggregateSummary agg={compareResult.baseline} title="Baseline" />
          <AggregateSummary agg={compareResult.variant} title="Variant" />
        </div>
      )}

      <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-4">
        <h2 className="font-display text-xl tracking-wide text-ink">Landing probability</h2>
        <p className="text-xs text-ink-soft">
          Steady-state chance of landing on each tile from dice movement alone (ignores jail hold time and mystery-card moves).
        </p>
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label className={labelClass}>Dice count</label>
            <select value={diceCount} onChange={(e) => setDiceCount(e.target.value)} className={fieldClass}>
              <option value="1">1 die</option>
              <option value="2">2 dice</option>
              <option value="3">3 dice</option>
              <option value="4">4 dice</option>
            </select>
          </div>
          <button
            disabled={busy || !boardKey}
            onClick={handleShowProbabilities}
            className="rounded border-2 border-ink bg-monopoly-gold px-3 py-2 text-sm font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50"
          >
            Compute
          </button>
        </div>
        {probTiles && (
          <ul className="flex flex-col gap-1">
            {[...probTiles].sort((a, b) => b.probability - a.probability).map((t) => (
              <li key={t.position} className="flex items-center gap-2 text-xs">
                <span className="w-32 shrink-0 truncate font-medium text-ink">{t.name}</span>
                <div className="h-3 flex-1 rounded bg-board">
                  <div
                    className="h-3 rounded bg-monopoly-red"
                    style={{ width: `${(t.probability / maxProb) * 100}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right font-mono text-ink-soft">{(t.probability * 100).toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
