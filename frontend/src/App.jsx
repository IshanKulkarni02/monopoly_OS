import { useEffect, useState } from 'react'
import Board from './components/Board'
import SettingsPanel from './components/SettingsPanel'
import GameSetup from './components/GameSetup'
import GameView from './components/GameView'
import {
  getTiles,
  createTile,
  updateTile,
  moveTile,
  deleteTile,
} from './api'
import './App.css'

function App() {
  const [view, setView] = useState('games') // 'games' | 'board'
  const [activeGameId, setActiveGameId] = useState(null)

  const [tiles, setTiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const refresh = () => getTiles().then(setTiles)

  useEffect(() => {
    refresh()
      .catch(() => setError('Could not reach the API'))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = (payload) => createTile(payload).then(refresh)
  const handleUpdate = (id, payload) => updateTile(id, payload).then(refresh)
  const handleMove = (id, direction) => moveTile(id, direction).then(setTiles)
  const handleDelete = (id) => deleteTile(id).then(setTiles)

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Monopoly Manager</h1>
        <nav className="main-nav">
          <button
            className={view === 'games' ? 'active' : ''}
            onClick={() => {
              setView('games')
              setActiveGameId(null)
            }}
          >
            Play
          </button>
          <button
            className={view === 'board' ? 'active' : ''}
            onClick={() => setView('board')}
          >
            Board editor
          </button>
        </nav>
        {view === 'board' && (
          <button className="settings-btn" onClick={() => setSettingsOpen(true)}>
            ⚙ Settings
          </button>
        )}
      </header>

      {view === 'games' &&
        (activeGameId ? (
          <GameView gameId={activeGameId} onExit={() => setActiveGameId(null)} />
        ) : (
          <GameSetup onGameStart={setActiveGameId} />
        ))}

      {view === 'board' && (
        <>
          {loading && <p className="status-text">Loading board...</p>}
          {error && <p className="status-text error">{error}</p>}
          {!loading && !error && <Board tiles={tiles} />}

          {settingsOpen && (
            <SettingsPanel
              tiles={tiles}
              onClose={() => setSettingsOpen(false)}
              onCreate={handleCreate}
              onUpdate={handleUpdate}
              onMove={handleMove}
              onDelete={handleDelete}
            />
          )}
        </>
      )}
    </div>
  )
}

export default App
