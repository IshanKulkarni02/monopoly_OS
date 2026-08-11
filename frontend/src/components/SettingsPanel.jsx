import { useState } from "react";
import TileForm from "./TileForm";
import { TILE_TYPE_LABELS } from "../boardLayout";
import "./SettingsPanel.css";

export default function SettingsPanel({
  tiles,
  onClose,
  onCreate,
  onUpdate,
  onMove,
  onDelete,
}) {
  const [editingId, setEditingId] = useState(null);
  const [creating, setCreating] = useState(false);

  const editingTile = tiles.find((t) => t._id === editingId);

  return (
    <div className="settings-overlay" role="dialog" aria-label="Board settings">
      <div className="settings-panel">
        <div className="settings-header">
          <h2>Board Settings</h2>
          <button className="close-btn" onClick={onClose} aria-label="Close settings">
            ×
          </button>
        </div>

        {!creating && !editingTile && (
          <>
            <button className="add-tile-btn" onClick={() => setCreating(true)}>
              + Add tile
            </button>
            <ul className="tile-list">
              {tiles.map((tile, idx) => (
                <li key={tile._id} className="tile-list-item">
                  <span className="tile-list-pos">{tile.position}</span>
                  <span className="tile-list-name">{tile.name}</span>
                  <span className="tile-list-type">{TILE_TYPE_LABELS[tile.type]}</span>
                  <div className="tile-list-actions">
                    <button onClick={() => onMove(tile._id, "up")} disabled={idx === 0}>
                      ↑
                    </button>
                    <button
                      onClick={() => onMove(tile._id, "down")}
                      disabled={idx === tiles.length - 1}
                    >
                      ↓
                    </button>
                    <button onClick={() => setEditingId(tile._id)}>Edit</button>
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}

        {creating && (
          <TileForm
            onSubmit={async (payload) => {
              await onCreate(payload);
              setCreating(false);
            }}
            onCancel={() => setCreating(false)}
          />
        )}

        {editingTile && (
          <TileForm
            tile={editingTile}
            onSubmit={async (payload) => {
              await onUpdate(editingTile._id, payload);
              setEditingId(null);
            }}
            onCancel={() => setEditingId(null)}
            onDelete={async () => {
              await onDelete(editingTile._id);
              setEditingId(null);
            }}
          />
        )}
      </div>
    </div>
  );
}
