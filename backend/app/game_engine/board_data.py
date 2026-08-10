"""Classic 40-space Monopoly board layout, prices, and rent tables.

Each space is a dict:
  index, name, type (go|property|railroad|utility|tax|chance|community_chest|
                      jail|free_parking|go_to_jail),
  price (purchase cost, purchasable types only),
  color (color-group key, property types only),
  rent (list of 6 rents for 0/1/2/3/4 houses/hotel, property types only;
        railroads and utilities compute rent dynamically instead),
  tax_amount (tax spaces only).
"""

CLASSIC_BOARD = [
    {"index": 0, "name": "GO", "type": "go"},
    {"index": 1, "name": "Mediterranean Avenue", "type": "property", "color": "brown", "price": 60,
     "rent": [2, 10, 30, 90, 160, 250]},
    {"index": 2, "name": "Community Chest", "type": "community_chest"},
    {"index": 3, "name": "Baltic Avenue", "type": "property", "color": "brown", "price": 60,
     "rent": [4, 20, 60, 180, 320, 450]},
    {"index": 4, "name": "Income Tax", "type": "tax", "tax_amount": 200},
    {"index": 5, "name": "Reading Railroad", "type": "railroad", "price": 200},
    {"index": 6, "name": "Oriental Avenue", "type": "property", "color": "light_blue", "price": 100,
     "rent": [6, 30, 90, 270, 400, 550]},
    {"index": 7, "name": "Chance", "type": "chance"},
    {"index": 8, "name": "Vermont Avenue", "type": "property", "color": "light_blue", "price": 100,
     "rent": [6, 30, 90, 270, 400, 550]},
    {"index": 9, "name": "Connecticut Avenue", "type": "property", "color": "light_blue", "price": 120,
     "rent": [8, 40, 100, 300, 450, 600]},
    {"index": 10, "name": "Jail", "type": "jail"},
    {"index": 11, "name": "St. Charles Place", "type": "property", "color": "pink", "price": 140,
     "rent": [10, 50, 150, 450, 625, 750]},
    {"index": 12, "name": "Electric Company", "type": "utility", "price": 150},
    {"index": 13, "name": "States Avenue", "type": "property", "color": "pink", "price": 140,
     "rent": [10, 50, 150, 450, 625, 750]},
    {"index": 14, "name": "Virginia Avenue", "type": "property", "color": "pink", "price": 160,
     "rent": [12, 60, 180, 500, 700, 900]},
    {"index": 15, "name": "Pennsylvania Railroad", "type": "railroad", "price": 200},
    {"index": 16, "name": "St. James Place", "type": "property", "color": "orange", "price": 180,
     "rent": [14, 70, 200, 550, 750, 950]},
    {"index": 17, "name": "Community Chest", "type": "community_chest"},
    {"index": 18, "name": "Tennessee Avenue", "type": "property", "color": "orange", "price": 180,
     "rent": [14, 70, 200, 550, 750, 950]},
    {"index": 19, "name": "New York Avenue", "type": "property", "color": "orange", "price": 200,
     "rent": [16, 80, 220, 600, 800, 1000]},
    {"index": 20, "name": "Free Parking", "type": "free_parking"},
    {"index": 21, "name": "Kentucky Avenue", "type": "property", "color": "red", "price": 220,
     "rent": [18, 90, 250, 700, 875, 1050]},
    {"index": 22, "name": "Chance", "type": "chance"},
    {"index": 23, "name": "Indiana Avenue", "type": "property", "color": "red", "price": 220,
     "rent": [18, 90, 250, 700, 875, 1050]},
    {"index": 24, "name": "Illinois Avenue", "type": "property", "color": "red", "price": 240,
     "rent": [20, 100, 300, 750, 925, 1100]},
    {"index": 25, "name": "B&O Railroad", "type": "railroad", "price": 200},
    {"index": 26, "name": "Atlantic Avenue", "type": "property", "color": "yellow", "price": 260,
     "rent": [22, 110, 330, 800, 975, 1150]},
    {"index": 27, "name": "Ventnor Avenue", "type": "property", "color": "yellow", "price": 260,
     "rent": [22, 110, 330, 800, 975, 1150]},
    {"index": 28, "name": "Water Works", "type": "utility", "price": 150},
    {"index": 29, "name": "Marvin Gardens", "type": "property", "color": "yellow", "price": 280,
     "rent": [24, 120, 360, 850, 1025, 1200]},
    {"index": 30, "name": "Go To Jail", "type": "go_to_jail"},
    {"index": 31, "name": "Pacific Avenue", "type": "property", "color": "green", "price": 300,
     "rent": [26, 130, 390, 900, 1100, 1275]},
    {"index": 32, "name": "North Carolina Avenue", "type": "property", "color": "green", "price": 300,
     "rent": [26, 130, 390, 900, 1100, 1275]},
    {"index": 33, "name": "Community Chest", "type": "community_chest"},
    {"index": 34, "name": "Pennsylvania Avenue", "type": "property", "color": "green", "price": 320,
     "rent": [28, 150, 450, 1000, 1200, 1400]},
    {"index": 35, "name": "Short Line", "type": "railroad", "price": 200},
    {"index": 36, "name": "Chance", "type": "chance"},
    {"index": 37, "name": "Park Place", "type": "property", "color": "dark_blue", "price": 350,
     "rent": [35, 175, 500, 1100, 1300, 1500]},
    {"index": 38, "name": "Luxury Tax", "type": "tax", "tax_amount": 100},
    {"index": 39, "name": "Boardwalk", "type": "property", "color": "dark_blue", "price": 400,
     "rent": [50, 200, 600, 1400, 1700, 2000]},
]

PURCHASABLE_TYPES = {"property", "railroad", "utility"}

RAILROAD_RENTS = [25, 50, 100, 200]  # indexed by (count owned by same owner - 1)
UTILITY_MULTIPLIERS = [4, 10]  # indexed by (count owned by same owner - 1); multiplies last dice roll


def space_by_index(index: int) -> dict:
    return CLASSIC_BOARD[index % len(CLASSIC_BOARD)]


def purchasable_spaces() -> list[dict]:
    return [s for s in CLASSIC_BOARD if s["type"] in PURCHASABLE_TYPES]
