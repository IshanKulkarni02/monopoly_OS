// Every edition from the rules-reference doc. Only variants with a
// `boardKey` are actually playable today — the rest are visible in the
// picker (per "give all options") but rejected at game creation until each
// gets its own engine built (most of these are architecturally closer to
// separate projects than incremental features: Deal is a card tableau with
// no board, Fortnite Edition runs on HP/combat, Speed is concurrent-timed,
// Empire is tower-height rent, Cheaters needs async hidden-action + call-out
// detection, Ultimate/Voice Banking need hardware/NLP integration).
export const VARIANTS = {
  classic: {
    label: "Classic Monopoly",
    description: "The standard 40-tile board and ruleset.",
    boardKey: "classic",
    implemented: true,
  },
  mega: {
    label: "Mega Edition",
    description: "52-tile board, one extra property per color group.",
    boardKey: "mega",
    implemented: true,
  },
  deal: {
    label: "Monopoly Deal",
    description: "Card-tableau game, no board — separate engine needed.",
    boardKey: null,
    implemented: false,
  },
  ultimate_banking: {
    label: "Ultimate Banking Edition",
    description: "Electronic banking unit + dynamic Event-card rent.",
    boardKey: null,
    implemented: false,
  },
  voice_banking: {
    label: "Voice Banking Edition",
    description: "NLP voice-command banking — needs speech integration.",
    boardKey: null,
    implemented: false,
  },
  speed: {
    label: "Monopoly Speed",
    description: "10-minute timed rounds, simultaneous movement, no rent.",
    boardKey: null,
    implemented: false,
  },
  empire: {
    label: "Monopoly Empire",
    description: "Billboard tower-height rent instead of houses/hotels.",
    boardKey: null,
    implemented: false,
  },
  fortnite: {
    label: "Fortnite Edition",
    description: "HP instead of cash, combat + storm mechanics.",
    boardKey: null,
    implemented: false,
  },
  gamer: {
    label: "Monopoly Gamer (Mario Kart)",
    description: "Asymmetric character powers, Power-Up Die.",
    boardKey: null,
    implemented: false,
  },
  cheaters: {
    label: "Cheaters Edition",
    description: "Hidden async cheat actions + call-out interrupts.",
    boardKey: null,
    implemented: false,
  },
};

export const VARIANT_KEYS = Object.keys(VARIANTS);
