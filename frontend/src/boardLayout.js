// Maps a tile position to a cell in an (N+1)x(N+1) grid, where N = tiles
// per side (boardSize / 4). Works for any board whose size divides evenly
// by 4 (classic: 40 tiles / 10 per side / 11x11 grid; mega: 52 tiles / 13
// per side / 14x14 grid). 0 = GO (bottom-right corner), positions increase
// counter-clockwise when read visually, i.e. clockwise around the board as
// normally played.
export function gridDimension(boardSize) {
  return boardSize / 4 + 1;
}

export function gridPlacement(position, boardSize = 40) {
  const side = boardSize / 4;
  const dim = side + 1;

  if (position === 0) return { row: dim, col: dim };
  if (position === side) return { row: dim, col: 1 };
  if (position === side * 2) return { row: 1, col: 1 };
  if (position === side * 3) return { row: 1, col: dim };

  if (position > 0 && position < side) {
    return { row: dim, col: dim - position };
  }
  if (position > side && position < side * 2) {
    return { row: dim - (position - side), col: 1 };
  }
  if (position > side * 2 && position < side * 3) {
    return { row: 1, col: position - side * 2 + 1 };
  }
  if (position > side * 3 && position < boardSize) {
    return { row: position - side * 3 + 1, col: dim };
  }
  return { row: Math.ceil(dim / 2), col: Math.ceil(dim / 2) };
}

export const COLOR_HEX = {
  brown: "#955436",
  lightblue: "#aae0fa",
  pink: "#d93a96",
  orange: "#f7941d",
  red: "#ed1b24",
  yellow: "#fef200",
  green: "#1fb25a",
  darkblue: "#0072bb",
};

export function tileIcon(tile) {
  switch (tile.type) {
    case "railroad":
      return "🚂";
    case "chance":
      return "❓";
    case "community_chest":
      return "🎁";
    case "utility":
      return /water/i.test(tile.name) ? "🚰" : "💡";
    case "tax":
      return "💰";
    case "jail":
      return "🔒";
    case "free_parking":
      return "🅿️";
    case "go_to_jail":
      return "🚨";
    default:
      return null;
  }
}

export const TILE_TYPE_LABELS = {
  go: "GO",
  property: "Property",
  railroad: "Railroad",
  utility: "Utility",
  chance: "Chance",
  community_chest: "Community Chest",
  tax: "Tax",
  jail: "Jail / Just Visiting",
  free_parking: "Free Parking",
  go_to_jail: "Go To Jail",
};
