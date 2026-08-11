function sameOwnerGroup(game, property) {
  return game.properties.filter((p) => p.type === "property" && p.color === property.color);
}

function ownsAll(group, ownerId) {
  return group.length > 0 && group.every((p) => String(p.ownerId) === String(ownerId));
}

// Returns 0 if no rent is owed (unowned, mortgaged, or the mover already
// owns it). `diceSum` is only used for utility rent.
export function computeRent(game, property, diceSum) {
  if (!property.ownerId || property.mortgaged) return 0;

  if (game.rules?.jailRentSuspended) {
    const owner = game.players.id(property.ownerId);
    if (owner?.inJail) return 0;
  }

  if (property.type === "property") {
    if (property.houses > 0) {
      return property.rent[property.houses] ?? 0;
    }
    const group = sameOwnerGroup(game, property);
    const base = property.rent[0] ?? 0;
    return ownsAll(group, property.ownerId) ? base * 2 : base;
  }

  if (property.type === "railroad") {
    const ownedCount = game.properties.filter(
      (p) => p.type === "railroad" && String(p.ownerId) === String(property.ownerId)
    ).length;
    const idx = Math.min(ownedCount, property.rent.length) - 1;
    return property.rent[idx] ?? 0;
  }

  if (property.type === "utility") {
    const ownedCount = game.properties.filter(
      (p) => p.type === "utility" && String(p.ownerId) === String(property.ownerId)
    ).length;
    const multiplier = ownedCount >= 2 ? property.rent[1] : property.rent[0];
    return (multiplier ?? 0) * (diceSum || 0);
  }

  return 0;
}
