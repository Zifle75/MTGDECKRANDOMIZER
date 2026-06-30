import requests
import random
import time
import os

SCRYFALL_URL = "https://api.scryfall.com/cards/search"
INVALID_FILE = "invalid_combos.txt"

HEADERS = {
    "User-Agent": "MTGCommanderRandomizer/1.0",
    "Accept": "application/json",
}

COLORS = ["W", "U", "B", "R", "G"]

TRIBES = [
    "Elf", "Zombie", "Dragon", "Goblin", "Angel", "Wizard", "Warrior",
    "Cleric", "Shaman", "Spirit", "Vampire", "Knight", "Beast", "Human",
    "Merfolk", "Cat", "Dog", "Snake", "Hydra", "Giant", "Rogue",
    "Insect", "Spider", "Frog"
]


def load_invalid_combos():
    if not os.path.exists(INVALID_FILE):
        print("[INIT] No invalid combo file found (yet)")
        return set()

    with open(INVALID_FILE, "r") as f:
        combos = set(line.strip() for line in f.readlines())
        print(f"[INIT] Loaded {len(combos)} invalid combos")
        return combos


def save_invalid_combo(combo_key):
    with open(INVALID_FILE, "a") as f:
        f.write(combo_key + "\n")


def random_color_identity():
    count = random.randint(1, 3)
    return tuple(sorted(random.sample(COLORS, count)))


def build_query(tribe, colors):
    color_str = "".join(colors)
    # is:commander covers legality (legendary creature, or partner/background, etc.)
    # more reliably than t:legendary t:creature
    return f"t:{tribe} id={color_str} is:commander"


def fetch_count(query):
    print(f"[QUERY] {query}")

    try:
        response = requests.get(
            SCRYFALL_URL,
            params={"q": query},
            headers=HEADERS,
        )

        if response.status_code != 200:
            print(f"[ERROR] HTTP {response.status_code} - {response.text[:200]}")
            return 0

        data = response.json()
        count = data.get("total_cards", 0)
        print(f"[RESULT] -> {count}")
        return count

    except Exception as e:
        print(f"[ERROR] {e}")
        return 0


def roll_until_valid():
    invalid_cache = load_invalid_combos()

    start_time = time.time()
    roll_count = 0

    while time.time() - start_time < 10:
        roll_count += 1

        tribe = random.choice(TRIBES)
        colors = random_color_identity()
        color_str = "".join(colors)

        combo_key = f"{tribe}|{color_str}"

        print(f"[ROLL {roll_count}] Trying {tribe} {colors}")

        if combo_key in invalid_cache:
            print(f"[CACHE HIT] {combo_key}")
            continue

        query = build_query(tribe, colors)
        count = fetch_count(query)

        if count >= 3:
            print(f"[SUCCESS] Found valid combo: {tribe} {colors} ({count} commanders)")
            return tribe, colors, count

        else:
            print(f"[INVALID] {combo_key}")
            save_invalid_combo(combo_key)
            invalid_cache.add(combo_key)

    print("[FALLBACK] Could not find valid combo in time")
    return None


if __name__ == "__main__":
    result = roll_until_valid()

    if result:
        tribe, colors, count = result
        print("\n=== FINAL RESULT ===")
        print(f"Tribe: {tribe}")
        print(f"Colors: {colors}")
        print(f"Commander Count: {count}")
    else:
        print("No valid combo found.")