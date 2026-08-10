export type SpaceType =
  | 'go'
  | 'property'
  | 'railroad'
  | 'utility'
  | 'tax'
  | 'chance'
  | 'community_chest'
  | 'jail'
  | 'free_parking'
  | 'go_to_jail'

export interface BoardSpace {
  index: number
  name: string
  type: SpaceType
  color?: string
  rent?: number[]
}

export const CLASSIC_BOARD: BoardSpace[] = [
  { index: 0, name: 'GO', type: 'go' },
  { index: 1, name: 'Mediterranean Avenue', type: 'property', color: 'brown', rent: [2, 10, 30, 90, 160, 250] },
  { index: 2, name: 'Community Chest', type: 'community_chest' },
  { index: 3, name: 'Baltic Avenue', type: 'property', color: 'brown', rent: [4, 20, 60, 180, 320, 450] },
  { index: 4, name: 'Income Tax', type: 'tax' },
  { index: 5, name: 'Reading Railroad', type: 'railroad' },
  { index: 6, name: 'Oriental Avenue', type: 'property', color: 'light_blue', rent: [6, 30, 90, 270, 400, 550] },
  { index: 7, name: 'Chance', type: 'chance' },
  { index: 8, name: 'Vermont Avenue', type: 'property', color: 'light_blue', rent: [6, 30, 90, 270, 400, 550] },
  { index: 9, name: 'Connecticut Avenue', type: 'property', color: 'light_blue', rent: [8, 40, 100, 300, 450, 600] },
  { index: 10, name: 'Jail', type: 'jail' },
  { index: 11, name: 'St. Charles Place', type: 'property', color: 'pink', rent: [10, 50, 150, 450, 625, 750] },
  { index: 12, name: 'Electric Company', type: 'utility' },
  { index: 13, name: 'States Avenue', type: 'property', color: 'pink', rent: [10, 50, 150, 450, 625, 750] },
  { index: 14, name: 'Virginia Avenue', type: 'property', color: 'pink', rent: [12, 60, 180, 500, 700, 900] },
  { index: 15, name: 'Pennsylvania Railroad', type: 'railroad' },
  { index: 16, name: 'St. James Place', type: 'property', color: 'orange', rent: [14, 70, 200, 550, 750, 950] },
  { index: 17, name: 'Community Chest', type: 'community_chest' },
  { index: 18, name: 'Tennessee Avenue', type: 'property', color: 'orange', rent: [14, 70, 200, 550, 750, 950] },
  { index: 19, name: 'New York Avenue', type: 'property', color: 'orange', rent: [16, 80, 220, 600, 800, 1000] },
  { index: 20, name: 'Free Parking', type: 'free_parking' },
  { index: 21, name: 'Kentucky Avenue', type: 'property', color: 'red', rent: [18, 90, 250, 700, 875, 1050] },
  { index: 22, name: 'Chance', type: 'chance' },
  { index: 23, name: 'Indiana Avenue', type: 'property', color: 'red', rent: [18, 90, 250, 700, 875, 1050] },
  { index: 24, name: 'Illinois Avenue', type: 'property', color: 'red', rent: [20, 100, 300, 750, 925, 1100] },
  { index: 25, name: 'B&O Railroad', type: 'railroad' },
  { index: 26, name: 'Atlantic Avenue', type: 'property', color: 'yellow', rent: [22, 110, 330, 800, 975, 1150] },
  { index: 27, name: 'Ventnor Avenue', type: 'property', color: 'yellow', rent: [22, 110, 330, 800, 975, 1150] },
  { index: 28, name: 'Water Works', type: 'utility' },
  { index: 29, name: 'Marvin Gardens', type: 'property', color: 'yellow', rent: [24, 120, 360, 850, 1025, 1200] },
  { index: 30, name: 'Go To Jail', type: 'go_to_jail' },
  { index: 31, name: 'Pacific Avenue', type: 'property', color: 'green', rent: [26, 130, 390, 900, 1100, 1275] },
  { index: 32, name: 'North Carolina Avenue', type: 'property', color: 'green', rent: [26, 130, 390, 900, 1100, 1275] },
  { index: 33, name: 'Community Chest', type: 'community_chest' },
  { index: 34, name: 'Pennsylvania Avenue', type: 'property', color: 'green', rent: [28, 150, 450, 1000, 1200, 1400] },
  { index: 35, name: 'Short Line', type: 'railroad' },
  { index: 36, name: 'Chance', type: 'chance' },
  { index: 37, name: 'Park Place', type: 'property', color: 'dark_blue', rent: [35, 175, 500, 1100, 1300, 1500] },
  { index: 38, name: 'Luxury Tax', type: 'tax' },
  { index: 39, name: 'Boardwalk', type: 'property', color: 'dark_blue', rent: [50, 200, 600, 1400, 1700, 2000] },
]

export const COLOR_SWATCH: Record<string, string> = {
  brown: '#8b5a2b',
  light_blue: '#7ec8e3',
  pink: '#d63384',
  orange: '#fd7e14',
  red: '#dc3545',
  yellow: '#ffc107',
  green: '#198754',
  dark_blue: '#0d3b8c',
}

export const HOUSE_COSTS: Record<string, number> = {
  brown: 50,
  light_blue: 50,
  pink: 100,
  orange: 100,
  red: 150,
  yellow: 150,
  green: 200,
  dark_blue: 200,
}

export function spaceByIndex(index: number): BoardSpace {
  return CLASSIC_BOARD[index % CLASSIC_BOARD.length]
}

export function colorGroupSpaceIndices(color: string): number[] {
  return CLASSIC_BOARD.filter((s) => s.color === color).map((s) => s.index)
}

export function formatMoney(amount: number): string {
  return `$${amount.toLocaleString()}`
}
