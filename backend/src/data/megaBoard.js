// Monopoly Mega Edition-style board: 52 tiles, one extra property per color
// group vs. the classic 40-tile board (per the "30% larger, extra property
// per group" brief). Tile names/prices here are this app's own synthetic
// Mega layout, not a reproduction of Hasbro's exact Mega Edition board —
// fully editable afterward via the board editor like any other board.
export const megaBoard = [
  { position: 0, name: "GO", type: "go" },

  // Bottom side (1-12)
  { position: 1, name: "Mediterranean Avenue", type: "property", color: "brown", price: 60, rent: [2, 10, 30, 90, 160, 250], houseCost: 50, mortgageValue: 30 },
  { position: 2, name: "Community Chest", type: "community_chest" },
  { position: 3, name: "Baltic Avenue", type: "property", color: "brown", price: 60, rent: [4, 20, 60, 180, 320, 450], houseCost: 50, mortgageValue: 30 },
  { position: 4, name: "Salvador Avenue", type: "property", color: "brown", price: 80, rent: [6, 30, 90, 270, 400, 550], houseCost: 50, mortgageValue: 40 },
  { position: 5, name: "Income Tax", type: "tax", taxAmount: 200 },
  { position: 6, name: "Reading Railroad", type: "railroad", price: 200, rent: [25, 50, 100, 200], mortgageValue: 100 },
  { position: 7, name: "Oriental Avenue", type: "property", color: "lightblue", price: 100, rent: [6, 30, 90, 270, 400, 550], houseCost: 50, mortgageValue: 50 },
  { position: 8, name: "Chance", type: "chance" },
  { position: 9, name: "Vermont Avenue", type: "property", color: "lightblue", price: 100, rent: [6, 30, 90, 270, 400, 550], houseCost: 50, mortgageValue: 50 },
  { position: 10, name: "Connecticut Avenue", type: "property", color: "lightblue", price: 120, rent: [8, 40, 100, 300, 450, 600], houseCost: 50, mortgageValue: 60 },
  { position: 11, name: "Sunset Lane", type: "property", color: "lightblue", price: 140, rent: [10, 50, 110, 330, 480, 650], houseCost: 50, mortgageValue: 70 },
  { position: 12, name: "Southern Railroad", type: "railroad", price: 200, rent: [25, 50, 100, 200], mortgageValue: 100 },

  { position: 13, name: "Jail / Just Visiting", type: "jail" },

  // Left side (14-25)
  { position: 14, name: "St. Charles Place", type: "property", color: "pink", price: 140, rent: [10, 50, 150, 450, 625, 750], houseCost: 100, mortgageValue: 70 },
  { position: 15, name: "Electric Company", type: "utility", price: 150, rent: [4, 10], mortgageValue: 75 },
  { position: 16, name: "States Avenue", type: "property", color: "pink", price: 140, rent: [10, 50, 150, 450, 625, 750], houseCost: 100, mortgageValue: 70 },
  { position: 17, name: "Virginia Avenue", type: "property", color: "pink", price: 160, rent: [12, 60, 180, 500, 700, 900], houseCost: 100, mortgageValue: 80 },
  { position: 18, name: "Fairview Avenue", type: "property", color: "pink", price: 180, rent: [14, 70, 200, 550, 750, 950], houseCost: 100, mortgageValue: 90 },
  { position: 19, name: "Pennsylvania Railroad", type: "railroad", price: 200, rent: [25, 50, 100, 200], mortgageValue: 100 },
  { position: 20, name: "St. James Place", type: "property", color: "orange", price: 180, rent: [14, 70, 200, 550, 750, 950], houseCost: 100, mortgageValue: 90 },
  { position: 21, name: "Community Chest", type: "community_chest" },
  { position: 22, name: "Tennessee Avenue", type: "property", color: "orange", price: 180, rent: [14, 70, 200, 550, 750, 950], houseCost: 100, mortgageValue: 90 },
  { position: 23, name: "New York Avenue", type: "property", color: "orange", price: 200, rent: [16, 80, 220, 600, 800, 1000], houseCost: 100, mortgageValue: 100 },
  { position: 24, name: "Liberty Avenue", type: "property", color: "orange", price: 220, rent: [18, 90, 240, 650, 850, 1050], houseCost: 100, mortgageValue: 110 },
  { position: 25, name: "Gasworks", type: "utility", price: 150, rent: [4, 10], mortgageValue: 75 },

  { position: 26, name: "Free Parking", type: "free_parking" },

  // Top side (27-38)
  { position: 27, name: "Kentucky Avenue", type: "property", color: "red", price: 220, rent: [18, 90, 250, 700, 875, 1050], houseCost: 150, mortgageValue: 110 },
  { position: 28, name: "Chance", type: "chance" },
  { position: 29, name: "Indiana Avenue", type: "property", color: "red", price: 220, rent: [18, 90, 250, 700, 875, 1050], houseCost: 150, mortgageValue: 110 },
  { position: 30, name: "Illinois Avenue", type: "property", color: "red", price: 240, rent: [20, 100, 300, 750, 925, 1100], houseCost: 150, mortgageValue: 120 },
  { position: 31, name: "Somerset Avenue", type: "property", color: "red", price: 260, rent: [22, 110, 320, 800, 975, 1150], houseCost: 150, mortgageValue: 130 },
  { position: 32, name: "B&O Railroad", type: "railroad", price: 200, rent: [25, 50, 100, 200], mortgageValue: 100 },
  { position: 33, name: "Atlantic Avenue", type: "property", color: "yellow", price: 260, rent: [22, 110, 330, 800, 975, 1150], houseCost: 150, mortgageValue: 130 },
  { position: 34, name: "Ventnor Avenue", type: "property", color: "yellow", price: 260, rent: [22, 110, 330, 800, 975, 1150], houseCost: 150, mortgageValue: 130 },
  { position: 35, name: "Water Works", type: "utility", price: 150, rent: [4, 10], mortgageValue: 75 },
  { position: 36, name: "Marvin Gardens", type: "property", color: "yellow", price: 280, rent: [24, 120, 360, 850, 1025, 1200], houseCost: 150, mortgageValue: 140 },
  { position: 37, name: "Highland Avenue", type: "property", color: "yellow", price: 300, rent: [26, 130, 380, 900, 1075, 1250], houseCost: 150, mortgageValue: 150 },
  { position: 38, name: "Community Chest", type: "community_chest" },

  { position: 39, name: "Go To Jail", type: "go_to_jail" },

  // Right side (40-51)
  { position: 40, name: "Pacific Avenue", type: "property", color: "green", price: 300, rent: [26, 130, 390, 900, 1100, 1275], houseCost: 200, mortgageValue: 150 },
  { position: 41, name: "North Carolina Avenue", type: "property", color: "green", price: 300, rent: [26, 130, 390, 900, 1100, 1275], houseCost: 200, mortgageValue: 150 },
  { position: 42, name: "Chance", type: "chance" },
  { position: 43, name: "Pennsylvania Avenue", type: "property", color: "green", price: 320, rent: [28, 150, 450, 1000, 1200, 1400], houseCost: 200, mortgageValue: 160 },
  { position: 44, name: "Crestwood Avenue", type: "property", color: "green", price: 340, rent: [30, 160, 470, 1050, 1250, 1450], houseCost: 200, mortgageValue: 170 },
  { position: 45, name: "Short Line", type: "railroad", price: 200, rent: [25, 50, 100, 200], mortgageValue: 100 },
  { position: 46, name: "Chance", type: "chance" },
  { position: 47, name: "Park Place", type: "property", color: "darkblue", price: 350, rent: [35, 175, 500, 1100, 1300, 1500], houseCost: 200, mortgageValue: 175 },
  { position: 48, name: "Community Chest", type: "community_chest" },
  { position: 49, name: "Boardwalk", type: "property", color: "darkblue", price: 400, rent: [50, 200, 600, 1400, 1700, 2000], houseCost: 200, mortgageValue: 200 },
  { position: 50, name: "Grandview Boulevard", type: "property", color: "darkblue", price: 450, rent: [60, 225, 650, 1500, 1800, 2100], houseCost: 200, mortgageValue: 225 },
  { position: 51, name: "Luxury Tax", type: "tax", taxAmount: 150 },
];
