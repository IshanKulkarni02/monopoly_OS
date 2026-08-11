import { gridPlacement, gridDimension, COLOR_HEX, tileIcon } from "../boardLayout";
import "./Board.css";

const CORNER_TYPES = ["go", "jail", "free_parking", "go_to_jail"];

function edgeOf(position, boardSize) {
  const side = boardSize / 4;
  if (position > 0 && position < side) return "bottom";
  if (position > side && position < side * 2) return "left";
  if (position > side * 2 && position < side * 3) return "top";
  if (position > side * 3 && position < boardSize) return "right";
  return "bottom";
}

function HousePips({ houses }) {
  if (!houses) return null;
  if (houses >= 5) {
    return <div className="tile-houses hotel-pip">🏨</div>;
  }
  return (
    <div className="tile-houses">
      {Array.from({ length: houses }).map((_, i) => (
        <span key={i} className="house-pip" />
      ))}
    </div>
  );
}

function BoardTile({ tile, boardSize, ownerColor, mortgaged, houses }) {
  const { row, col } = gridPlacement(tile.position, boardSize);
  const isCorner = CORNER_TYPES.includes(tile.type);
  const style = { gridRow: row, gridColumn: col };
  const edge = edgeOf(tile.position, boardSize);
  const icon = tileIcon(tile);

  if (isCorner) {
    return (
      <div className={`board-tile corner corner-${tile.type}`} style={style}>
        {tile.type === "go" && (
          <>
            <span className="corner-arrow">➜</span>
            <span className="corner-label go-label">GO</span>
          </>
        )}
        {tile.type !== "go" && (
          <>
            {icon && <span className="corner-icon">{icon}</span>}
            <span className="corner-label">{tile.name}</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div
      className={`board-tile edge-${edge} type-${tile.type} ${mortgaged ? "mortgaged" : ""}`}
      style={style}
    >
      {tile.color && (
        <div
          className="tile-color-bar"
          style={{ backgroundColor: COLOR_HEX[tile.color] }}
        />
      )}
      {ownerColor && (
        <div className="tile-owner-badge" style={{ backgroundColor: ownerColor }} />
      )}
      <HousePips houses={houses} />
      {icon && <div className="tile-icon">{icon}</div>}
      <div className="tile-name">{tile.name}</div>
      {tile.price != null && <div className="tile-price">${tile.price}</div>}
      {tile.taxAmount != null && (
        <div className="tile-price">${tile.taxAmount}</div>
      )}
    </div>
  );
}

function PlayerToken({ player, boardSize, index, total }) {
  const { row, col } = gridPlacement(player.position, boardSize);
  const style = { gridRow: row, gridColumn: col };
  const angle = total > 1 ? (360 / total) * index : 0;
  const radius = total > 1 ? 26 : 0;
  const dx = radius * Math.cos((angle * Math.PI) / 180);
  const dy = radius * Math.sin((angle * Math.PI) / 180);

  return (
    <div className="player-token-cell" style={style}>
      <span
        className="player-token"
        style={{
          backgroundColor: player.color,
          transform: `translate(${dx}%, ${dy}%)`,
        }}
        title={`${player.name} (${player.cash != null ? "$" + player.cash : ""})`}
      >
        {player.name.slice(0, 2).toUpperCase()}
      </span>
    </div>
  );
}

export default function Board({ tiles, players = [], properties = [] }) {
  const boardSize = tiles.length || 40;
  const dim = gridDimension(boardSize);

  const propertyByPosition = {};
  properties.forEach((p) => {
    propertyByPosition[p.position] = p;
  });
  const ownerColorById = {};
  players.forEach((p) => {
    ownerColorById[p._id] = p.color;
  });

  const positionGroups = {};
  players.forEach((p) => {
    if (!positionGroups[p.position]) positionGroups[p.position] = [];
    positionGroups[p.position].push(p);
  });

  return (
    <div className="board-wrapper">
      <div
        className="board-grid"
        style={{
          gridTemplateColumns: `repeat(${dim}, 1fr)`,
          gridTemplateRows: `repeat(${dim}, 1fr)`,
        }}
      >
        {tiles.map((tile) => {
          const property = propertyByPosition[tile.position];
          const ownerColor = property?.ownerId ? ownerColorById[property.ownerId] : null;
          return (
            <BoardTile
              key={tile._id}
              tile={tile}
              boardSize={boardSize}
              ownerColor={ownerColor}
              mortgaged={!!property?.mortgaged}
              houses={property?.houses || 0}
            />
          );
        })}
        {players.map((p) => {
          const group = positionGroups[p.position] || [p];
          return (
            <PlayerToken
              key={p._id}
              player={p}
              boardSize={boardSize}
              index={group.indexOf(p)}
              total={group.length}
            />
          );
        })}
        <div
          className="board-center"
          style={{ gridRow: `2 / ${dim}`, gridColumn: `2 / ${dim}` }}
        >
          <span className="brand-monopoly">MONOPOLY</span>
          <span className="brand-manager">Manager</span>
        </div>
      </div>
    </div>
  );
}
