import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BoardMap } from '../components/BoardMap'
import { BoardProvider } from '../hooks/useBoard'
import { useAccount } from '../hooks/useAccount'
import {
  createGroup,
  deleteBoardTemplate,
  getBoard,
  insertTile,
  moveTile,
  regenerateLayout,
  removeTile,
  updateBoard,
  updateGroup,
  updateTile,
} from '../api/client'
import type { TileFieldsInput } from '../api/client'
import type { BoardDetailOut, BoardTileOut } from '../api/types'
import { DEFAULT_CURRENCY } from '../boardData'

const fieldClass =
  'w-full rounded border-2 border-ink bg-board-card p-2 text-sm text-ink placeholder:text-ink-soft focus:outline-none focus:ring-2 focus:ring-monopoly-red'
const labelClass = 'text-xs font-bold uppercase tracking-wide text-ink-soft'
const KINDS = ['go', 'property', 'mystery', 'tax', 'jail', 'vacation', 'go_to_jail', 'custom']
const RENT_MODELS = ['fixed_table', 'group_count_table', 'dice_multiplier_table']

function parseNumberList(text: string): number[] {
  return text
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map(Number)
    .filter((n) => !Number.isNaN(n))
}

function TileEditForm({
  boardKey,
  tile,
  groups,
  sessionToken,
  onSaved,
  onClose,
}: {
  boardKey: string
  tile: BoardTileOut
  groups: BoardDetailOut['groups']
  sessionToken: string
  onSaved: (board: BoardDetailOut) => void
  onClose: () => void
}) {
  const [name, setName] = useState(tile.name)
  const [kind, setKind] = useState<string>(tile.kind)
  const [groupId, setGroupId] = useState(tile.group_id ?? '')
  const [price, setPrice] = useState(tile.price?.toString() ?? '')
  const [rentModel, setRentModel] = useState<string>(tile.rent_model)
  const [rentTable, setRentTable] = useState(tile.rent_table.join(', '))
  const [upgradeCosts, setUpgradeCosts] = useState(tile.upgrade_costs.join(', '))
  const [mortgageValue, setMortgageValue] = useState(tile.mortgage_value?.toString() ?? '')
  const [taxFormula, setTaxFormula] = useState((tile.tax_config.formula as string) ?? 'fixed')
  const [taxAmount, setTaxAmount] = useState(tile.tax_config.amount?.toString() ?? '')
  const [taxPercent, setTaxPercent] = useState(tile.tax_config.percent?.toString() ?? '')
  const [deckKey, setDeckKey] = useState(tile.mystery_deck_key)
  const [locked, setLocked] = useState(tile.locked)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function save() {
    setError(null)
    setBusy(true)
    const fields: TileFieldsInput = {
      name,
      kind,
      group_id: groupId || null,
      locked,
    }
    if (kind === 'property') {
      fields.price = price ? Number(price) : null
      fields.rent_model = rentModel
      fields.rent_table = parseNumberList(rentTable)
      fields.upgrade_costs = parseNumberList(upgradeCosts)
      fields.mortgage_value = mortgageValue ? Number(mortgageValue) : null
    }
    if (kind === 'tax') {
      fields.tax_config = { formula: taxFormula, amount: taxAmount ? Number(taxAmount) : undefined, percent: taxPercent ? Number(taxPercent) : undefined }
    }
    if (kind === 'mystery') {
      fields.mystery_deck_key = deckKey
    }
    try {
      const board = await updateTile(boardKey, tile.id, sessionToken, fields)
      onSaved(board)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save tile')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded border-2 border-monopoly-green bg-board p-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Kind</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)} className={fieldClass}>
            {KINDS.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
        </div>
      </div>

      {kind === 'property' && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelClass}>Group</label>
              <select value={groupId} onChange={(e) => setGroupId(e.target.value)} className={fieldClass}>
                <option value="">— none —</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Price</label>
              <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} className={fieldClass} />
            </div>
          </div>
          <div>
            <label className={labelClass}>Rent model</label>
            <select value={rentModel} onChange={(e) => setRentModel(e.target.value)} className={fieldClass}>
              {RENT_MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>Rent table (comma-separated, by upgrade level)</label>
            <input value={rentTable} onChange={(e) => setRentTable(e.target.value)} placeholder="2, 10, 30, 90" className={fieldClass} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className={labelClass}>Upgrade costs (comma-separated)</label>
              <input value={upgradeCosts} onChange={(e) => setUpgradeCosts(e.target.value)} placeholder="50, 50, 50" className={fieldClass} />
            </div>
            <div>
              <label className={labelClass}>Mortgage value</label>
              <input
                type="number"
                placeholder="Auto (50% of price)"
                value={mortgageValue}
                onChange={(e) => setMortgageValue(e.target.value)}
                className={fieldClass}
              />
            </div>
          </div>
        </>
      )}

      {kind === 'tax' && (
        <div className="grid grid-cols-3 gap-2">
          <div>
            <label className={labelClass}>Formula</label>
            <select value={taxFormula} onChange={(e) => setTaxFormula(e.target.value)} className={fieldClass}>
              <option value="fixed">Fixed</option>
              <option value="percent_cash">% of cash</option>
              <option value="percent_assets">% of assets</option>
            </select>
          </div>
          {taxFormula === 'fixed' ? (
            <div>
              <label className={labelClass}>Amount</label>
              <input type="number" value={taxAmount} onChange={(e) => setTaxAmount(e.target.value)} className={fieldClass} />
            </div>
          ) : (
            <div>
              <label className={labelClass}>Percent (0–1)</label>
              <input type="number" step="0.01" value={taxPercent} onChange={(e) => setTaxPercent(e.target.value)} className={fieldClass} />
            </div>
          )}
        </div>
      )}

      {kind === 'mystery' && (
        <div>
          <label className={labelClass}>Deck key</label>
          <input value={deckKey} onChange={(e) => setDeckKey(e.target.value)} placeholder="mystery" className={fieldClass} />
        </div>
      )}

      <label className="flex items-center gap-2 text-xs font-bold text-ink-soft">
        <input type="checkbox" checked={locked} onChange={(e) => setLocked(e.target.checked)} />
        Lock position (skip when regenerating layout)
      </label>

      {error && <p className="text-xs font-semibold text-monopoly-red">{error}</p>}
      <div className="flex gap-2">
        <button disabled={busy} onClick={save} className="rounded border-2 border-ink bg-monopoly-green px-3 py-1.5 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50">
          Save tile
        </button>
        <button onClick={onClose} className="rounded border-2 border-ink px-3 py-1.5 text-sm font-bold text-ink-soft hover:bg-board-card">
          Cancel
        </button>
      </div>
    </div>
  )
}

export function BoardEditor() {
  const { key = '' } = useParams()
  const { account } = useAccount()
  const navigate = useNavigate()
  const [board, setBoard] = useState<BoardDetailOut | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editingTileId, setEditingTileId] = useState<string | null>(null)
  const [moveFromId, setMoveFromId] = useState<string | null>(null)
  const [insertPosition, setInsertPosition] = useState('0')
  const [insertName, setInsertName] = useState('New tile')
  const [insertKind, setInsertKind] = useState('custom')
  const [newGroupKey, setNewGroupKey] = useState('')
  const [newGroupName, setNewGroupName] = useState('')
  const [newGroupColor, setNewGroupColor] = useState('#888888')
  const [constraints, setConstraints] = useState<Record<string, { min_gap: string; max_gap: string }>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getBoard(key)
      .then(setBoard)
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'Could not load board'))
  }, [key])

  if (!account) {
    return (
      <div className="mx-auto max-w-md p-6 text-center">
        <p className="font-semibold text-ink">Sign in from the home page to edit boards.</p>
      </div>
    )
  }
  if (loadError) return <div className="mx-auto max-w-md p-6 text-center text-monopoly-red">{loadError}</div>
  if (!board) return <div className="mx-auto max-w-md p-6 text-center text-ink-soft">Loading board…</div>
  if (board.owner_user_id !== account.user.id) {
    return (
      <div className="mx-auto max-w-md p-6 text-center">
        <p className="font-semibold text-ink">You don't own this board — duplicate it from the home page first.</p>
      </div>
    )
  }

  async function guarded(fn: () => Promise<BoardDetailOut>) {
    setError(null)
    setBusy(true)
    try {
      setBoard(await fn())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const sortedTiles = [...board.tiles].sort((a, b) => a.position - b.position)
  const groupById = (id: string | null) => board.groups.find((g) => g.id === id)

  return (
    <BoardProvider tiles={board.tiles} groups={board.groups} currency={DEFAULT_CURRENCY}>
      <div className="mx-auto flex max-w-2xl flex-col gap-4 p-4 pb-16">
        <div className="flex items-center justify-between">
          <button onClick={() => navigate('/')} className="text-sm font-bold text-monopoly-green hover:underline">
            ← Home
          </button>
          <button
            disabled={busy}
            onClick={() =>
              guarded(async () => {
                await deleteBoardTemplate(board.key, account.sessionToken)
                navigate('/')
                return board
              })
            }
            className="text-xs font-bold text-monopoly-red hover:underline"
          >
            Delete board
          </button>
        </div>

        <div className="rounded border-2 border-ink bg-board-card p-3">
          <input
            value={board.name}
            onBlur={(e) => guarded(() => updateBoard(board.key, account.sessionToken, { name: e.target.value }))}
            onChange={(e) => setBoard({ ...board, name: e.target.value })}
            className="w-full bg-transparent font-display text-xl tracking-wide text-ink focus:outline-none"
          />
          <input
            value={board.description}
            onBlur={(e) => guarded(() => updateBoard(board.key, account.sessionToken, { description: e.target.value }))}
            onChange={(e) => setBoard({ ...board, description: e.target.value })}
            className="mt-1 w-full bg-transparent text-sm text-ink-soft focus:outline-none"
            placeholder="Description"
          />
          <p className="mt-1 text-xs font-medium text-ink-soft">{board.size} tiles · key: {board.key}</p>
        </div>

        {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}

        <BoardMap
          players={[]}
          pickMode={moveFromId !== null}
          pickLabel={moveFromId ? 'Swap with…' : undefined}
          onPickTile={(position) => {
            if (!moveFromId) return
            const target = board.tiles.find((t) => t.position === position)
            if (!target || target.id === moveFromId) {
              setMoveFromId(null)
              return
            }
            guarded(() => moveTile(board.key, moveFromId, target.id, account.sessionToken)).then(() => setMoveFromId(null))
          }}
        />

        <div>
          <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Tiles ({sortedTiles.length})</h2>
          <div className="flex flex-col gap-1.5">
            {sortedTiles.map((tile) => {
              const group = groupById(tile.group_id)
              if (editingTileId === tile.id) {
                return (
                  <TileEditForm
                    key={tile.id}
                    boardKey={board.key}
                    tile={tile}
                    groups={board.groups}
                    sessionToken={account.sessionToken}
                    onSaved={setBoard}
                    onClose={() => setEditingTileId(null)}
                  />
                )
              }
              return (
                <div
                  key={tile.id}
                  className="flex items-center gap-2 rounded border-2 border-ink bg-board-card p-2"
                  style={group ? { borderLeftWidth: 8, borderLeftColor: group.color } : undefined}
                >
                  <span className="w-6 shrink-0 text-center font-mono text-xs text-ink-soft">{tile.position}</span>
                  <div className="flex-1">
                    <div className="text-sm font-bold text-ink">
                      {tile.name} {tile.locked && '🔒'}
                    </div>
                    <div className="text-xs font-medium text-ink-soft">
                      {tile.kind}
                      {tile.price != null ? ` · ${tile.price}` : ''}
                    </div>
                  </div>
                  <button
                    onClick={() => setMoveFromId(moveFromId === tile.id ? null : tile.id)}
                    className={`rounded border-2 border-ink px-2 py-1 text-xs font-bold ${moveFromId === tile.id ? 'bg-monopoly-gold text-ink' : 'text-ink hover:bg-board'}`}
                  >
                    Move
                  </button>
                  <button onClick={() => setEditingTileId(tile.id)} className="rounded border-2 border-ink px-2 py-1 text-xs font-bold text-ink hover:bg-board">
                    Edit
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => guarded(() => removeTile(board.key, tile.id, account.sessionToken))}
                    className="rounded border-2 border-ink px-2 py-1 text-xs font-bold text-monopoly-red hover:bg-board disabled:opacity-50"
                  >
                    ✕
                  </button>
                </div>
              )
            })}
          </div>
        </div>

        <div className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
          <h2 className="text-xs font-bold uppercase tracking-wide text-ink-soft">Add a tile</h2>
          <div className="grid grid-cols-3 gap-2">
            <input type="number" min={0} max={board.size} value={insertPosition} onChange={(e) => setInsertPosition(e.target.value)} className={fieldClass} placeholder="Position" />
            <input value={insertName} onChange={(e) => setInsertName(e.target.value)} className={fieldClass} placeholder="Name" />
            <select value={insertKind} onChange={(e) => setInsertKind(e.target.value)} className={fieldClass}>
              {KINDS.map((k) => (
                <option key={k} value={k}>{k}</option>
              ))}
            </select>
          </div>
          <button
            disabled={busy}
            onClick={() =>
              guarded(() => insertTile(board.key, account.sessionToken, { position: Number(insertPosition), name: insertName, kind: insertKind }))
            }
            className="rounded border-2 border-ink bg-monopoly-green py-2 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
          >
            Insert tile
          </button>
        </div>

        <div className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
          <h2 className="text-xs font-bold uppercase tracking-wide text-ink-soft">Groups</h2>
          {board.groups.map((g) => (
            <div key={g.id} className="flex items-center gap-2 text-sm">
              <span className="h-4 w-4 rounded-full border border-ink" style={{ background: g.color }} />
              <input
                defaultValue={g.name}
                onBlur={(e) => guarded(() => updateGroup(board.key, g.id, account.sessionToken, { name: e.target.value }))}
                className="flex-1 rounded border-2 border-ink bg-board p-1 text-ink"
              />
              <input
                type="color"
                defaultValue={g.color}
                onBlur={(e) => guarded(() => updateGroup(board.key, g.id, account.sessionToken, { color: e.target.value }))}
                className="h-8 w-10 border-2 border-ink"
              />
              <input
                type="number"
                placeholder="× rent"
                defaultValue={g.rent_multiplier ?? ''}
                onBlur={(e) => guarded(() => updateGroup(board.key, g.id, account.sessionToken, { rent_multiplier: e.target.value ? Number(e.target.value) : null }))}
                className="w-20 rounded border-2 border-ink bg-board p-1 text-xs text-ink"
              />
            </div>
          ))}
          <div className="grid grid-cols-3 gap-2 pt-2">
            <input placeholder="key" value={newGroupKey} onChange={(e) => setNewGroupKey(e.target.value)} className={fieldClass} />
            <input placeholder="name" value={newGroupName} onChange={(e) => setNewGroupName(e.target.value)} className={fieldClass} />
            <input type="color" value={newGroupColor} onChange={(e) => setNewGroupColor(e.target.value)} className="h-9 border-2 border-ink" />
          </div>
          <button
            disabled={busy || !newGroupKey || !newGroupName}
            onClick={() =>
              guarded(() => createGroup(board.key, account.sessionToken, { key: newGroupKey, name: newGroupName, color: newGroupColor })).then(() => {
                setNewGroupKey('')
                setNewGroupName('')
              })
            }
            className="rounded border-2 border-ink bg-board py-2 text-sm font-bold text-ink hover:bg-monopoly-gold disabled:opacity-50"
          >
            + Add group
          </button>
        </div>

        <div className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
          <h2 className="text-xs font-bold uppercase tracking-wide text-ink-soft">Generator — regenerate layout</h2>
          <p className="text-xs text-ink-soft">Locked tiles (🔒) and corner tiles never move. Leave gaps blank for no constraint.</p>
          {board.groups.map((g) => {
            const c = constraints[g.key] ?? { min_gap: '', max_gap: '' }
            return (
              <div key={g.id} className="grid grid-cols-3 items-center gap-2 text-sm">
                <span className="font-bold text-ink">{g.name}</span>
                <input
                  type="number"
                  placeholder="min gap"
                  value={c.min_gap}
                  onChange={(e) => setConstraints({ ...constraints, [g.key]: { ...c, min_gap: e.target.value } })}
                  className={`${fieldClass} p-1.5`}
                />
                <input
                  type="number"
                  placeholder="max gap"
                  value={c.max_gap}
                  onChange={(e) => setConstraints({ ...constraints, [g.key]: { ...c, max_gap: e.target.value } })}
                  className={`${fieldClass} p-1.5`}
                />
              </div>
            )
          })}
          <button
            disabled={busy}
            onClick={() =>
              guarded(() =>
                regenerateLayout(board.key, account.sessionToken, {
                  groupConstraints: Object.fromEntries(
                    Object.entries(constraints).map(([k, v]) => [
                      k,
                      { min_gap: v.min_gap ? Number(v.min_gap) : null, max_gap: v.max_gap ? Number(v.max_gap) : null },
                    ]),
                  ),
                }),
              )
            }
            className="rounded border-2 border-ink bg-monopoly-gold py-2 text-sm font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50"
          >
            🎲 Regenerate layout
          </button>
        </div>
      </div>
    </BoardProvider>
  )
}
