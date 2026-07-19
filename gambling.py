"""
Wheel of Tribes (Vegas Slot Machine Edition)
A desktop Commander tribal randomizer: set up your table, roll each player a
tribe + color identity on a two-reel slot machine, reroll anyone who wants a
new fate.

Requires: requests   (pip install requests)
Run:      python wheel_of_tribes.py
"""

import json
import os
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import ttk
import requests

# ---------------------------------------------------------------------------
# Config / constants
# ---------------------------------------------------------------------------

SCRYFALL_URL = "https://api.scryfall.com/cards/search"
INVALID_TRIBES_FILE = "invalid_tribes.txt"      # tribes with no color identity that has >=2 commanders
TRIBE_CACHE_FILE = "tribe_identity_cache.json"  # per-tribe color-identity results, cached >=24h
WEIGHTS_FILE = "color_weights.json"             # persisted +1 weighting per color combination
TRIBE_CACHE_TTL_SECONDS = 24 * 60 * 60          # Scryfall asks that gameplay data be cached at least a day

COLORS = ["W", "U", "B", "R", "G"]

TRIBES = [
    "Advisor", "Aetherborn", "Alien", "Ally", "Angel", "Antelope", "Ape", "Archer",
    "Archon", "Armadillo", "Army", "Artificer", "Assassin", "Assembly-Worker",
    "Astartes", "Atog", "Aurochs", "Avatar", "Azra", "Badger", "Balloon", "Barbarian",
    "Bard", "Basilisk", "Bat", "Beaver", "Bear", "Beast", "Beeble", "Beholder",
    "Berserker", "Bird", "Blinkmoth", "Boar", "Bringer", "Brushwagg", "Camarid",
    "Camel", "Capybara", "Caribou", "Carrier", "Cat", "Centaur", "Child", "Chimera",
    "Citizen", "Cleric", "Clown", "Cockatrice", "Construct", "Coward", "Coyote",
    "Crab", "Crocodile", "Ctan", "Custodes", "Cyberman", "Cyclops", "Dalek",
    "Dauthi", "Demigod", "Demon", "Deserter", "Detective", "Devil", "Dinosaur",
    "Djinn", "Doctor", "Dog", "Dragon", "Drake", "Dreadnought", "Drone", "Druid",
    "Dryad", "Dwarf", "Efreet", "Egg", "Elder", "Eldrazi", "Elemental", "Elephant",
    "Elf", "Elk", "Employee", "Eye", "Faerie", "Ferret", "Fish", "Flagbearer",
    "Fox", "Fractal", "Frog", "Fungus", "Gamer", "Gargoyle", "Germ", "Giant",
    "Gith", "Glimmer", "Gnoll", "Gnome", "Goat", "Goblin", "God", "Golem",
    "Gorgon", "Graveborn", "Gremlin", "Griffin", "Guest", "Hag", "Halfling",
    "Hamster", "Harpy", "Hellion", "Hero", "Hippo", "Hippogriff", "Homarid",
    "Homunculus", "Horror", "Horse", "Human", "Hydra", "Hyena", "Illusion",
    "Imp", "Incarnation", "Inkling", "Inquisitor", "Insect", "Jackal", "Jellyfish",
    "Juggernaut", "Kavu", "Kirin", "Kithkin", "Knight", "Kobold", "Kor", "Kraken",
    "Lamia", "Lammasu", "Leech", "Leviathan", "Lhurgoyf", "Licid", "Lizard",
    "Llama", "Manticore", "Masticore", "Mercenary", "Merfolk", "Metathran",
    "Minion", "Minotaur", "Mite", "Mole", "Monger", "Mongoose", "Monk", "Monkey",
    "Moonfolk", "Mount", "Mouse", "Mutant", "Myr", "Mystic", "Nautilus", "Necron",
    "Nephilim", "Nightmare", "Nightstalker", "Ninja", "Noble", "Noggle", "Nomad",
    "Nymph", "Octopus", "Ogre", "Ooze", "Orb", "Orc", "Orgg", "Otter", "Ouphe",
    "Ox", "Oyster", "Pangolin", "Peasant", "Pegasus", "Pentavite", "Performer",
    "Pest", "Phelddagrif", "Phoenix", "Phyrexian", "Pilot", "Pincher", "Pirate",
    "Plant", "Porcupine", "Possum", "Praetor", "Primarch", "Prism", "Processor",
    "Raccoon", "Rabbit", "Ranger", "Rat", "Rebel", "Reflection", "Rhino", "Rigger",
    "Robot", "Rogue", "Sable", "Salamander", "Samurai", "Sand", "Saproling",
    "Satyr", "Scarecrow", "Scientist", "Scion", "Scorpion", "Scout", "Sculpture",
    "Serf", "Serpent", "Servo", "Shade", "Shaman", "Shapeshifter", "Shark",
    "Sheep", "Siren", "Skeleton", "Skunk", "Slith", "Sliver", "Sloth", "Slug",
    "Snail", "Snake", "Soldier", "Soltari", "Spawn", "Specter", "Spellshaper",
    "Sphinx", "Spider", "Spike", "Spirit", "Splinter", "Sponge", "Spy", "Squid",
    "Squirrel", "Starfish", "Surrakar", "Survivor", "Synth", "Tentacle",
    "Tetravite", "Thalakos", "Thopter", "Thrull", "Tiefling", "Time Lord", "Toy",
    "Treefolk", "Trilobite", "Triskelavite", "Troll", "Turtle", "Tyranid",
    "Unicorn", "Vampire", "Varmint", "Vedalken", "Villain", "Volver", "Wall",
    "Walrus", "Warlock", "Warrior", "Weasel", "Weird", "Werewolf", "Whale",
    "Wizard", "Wolf", "Wolverine", "Wombat", "Worm", "Wraith", "Wurm",
    "Yeti", "Zombie", "Zubera"
]

# Color identity -> common Magic name (guilds / wedges / shards / 4-color / 5-color)
# Colors in the tuples must be sorted alphabetically: B, G, R, U, W
COLOR_IDENTITY_NAMES = {
    ("W",): "Mono White",
    ("U",): "Mono Blue",
    ("B",): "Mono Black",
    ("R",): "Mono Red",
    ("G",): "Mono Green",
    ("U", "W"): "Azorius",
    ("B", "W"): "Orzhov",
    ("R", "W"): "Boros",
    ("G", "W"): "Selesnya",
    ("B", "U"): "Dimir",
    ("R", "U"): "Izzet",
    ("G", "U"): "Simic",
    ("B", "R"): "Rakdos",
    ("B", "G"): "Golgari",
    ("G", "R"): "Gruul",
    ("B", "U", "W"): "Esper",
    ("R", "U", "W"): "Jeskai",
    ("G", "U", "W"): "Bant",
    ("B", "R", "W"): "Mardu",
    ("B", "G", "W"): "Abzan",
    ("G", "R", "W"): "Naya",
    ("B", "R", "U"): "Grixis",
    ("B", "G", "U"): "Sultai",
    ("G", "R", "U"): "Temur",
    ("B", "G", "R"): "Jund",
    # 4-Color (Alphabetically sorted keys)
    ("B", "G", "R", "U"): "Sans-White",
    ("B", "G", "R", "W"): "Sans-Blue",
    ("G", "R", "U", "W"): "Sans-Black",
    ("B", "G", "U", "W"): "Sans-Red",
    ("B", "R", "U", "W"): "Sans-Green",
    # 5-Color
    ("B", "G", "R", "U", "W"): "5-Color",
}

COLOR_HEX = {
    "W": "#F2E9C9",
    "U": "#33B5E5",
    "B": "#B07CFF",
    "R": "#FF4D4D",
    "G": "#4BD17B",
}

# ---- Vegas theme palette ---------------------------------------------------
BG_VOID = "#0A0A0F"          
BG_CARD = "#14241C"          
BG_CARD_2 = "#1D3327"        
LINE = "#3A2A12"             
PARCHMENT = "#F4E9D8"
PARCHMENT_DIM = "#B9A98A"
GOLD = "#FFD447"
GOLD_BRIGHT = "#FFE98A"
NEON_PINK = "#FF2DA0"
NEON_CYAN = "#27E6E6"
GREEN_OK = "#5CFF9D"
RED_ERR = "#FF5D5D"
REEL_DARK_TEXT = "#0A0A0F"

ROLL_TIMEOUT_SECONDS = 25  
HEADERS = {
    "User-Agent": "WheelOfTribesApp/1.0",
    "Accept": "application/json",
}

def identity_name(colors):
    key = tuple(sorted(colors))
    return COLOR_IDENTITY_NAMES.get(key, "/".join(key) if key else "Colorless")

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return "#%02X%02X%02X" % rgb

def identity_color(colors):
    if not colors:
        return "#8A8A8A"  
    rgbs = [_hex_to_rgb(COLOR_HEX[c]) for c in colors]
    avg = tuple(sum(ch) // len(ch) for ch in zip(*rgbs))
    return _rgb_to_hex(avg)

ALL_IDENTITIES = [
    (identity_name(key), identity_color(key)) for key in COLOR_IDENTITY_NAMES
]

# ---------------------------------------------------------------------------
# Persisted caches
# ---------------------------------------------------------------------------

def load_invalid_tribes():
    if not os.path.exists(INVALID_TRIBES_FILE):
        return set()
    with open(INVALID_TRIBES_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_invalid_tribe(tribe):
    with open(INVALID_TRIBES_FILE, "a") as f:
        f.write(tribe + "\n")

def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default

def save_json_file(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

invalid_tribe_cache = load_invalid_tribes()
tribe_identity_cache = load_json_file(TRIBE_CACHE_FILE, {})
color_weights = load_json_file(WEIGHTS_FILE, {})

_cache_lock = threading.Lock()      
_weights_lock = threading.Lock()    

# ---------------------------------------------------------------------------
# Scryfall rate limiting
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, min_interval_seconds):
        self.min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_request = 0.0

    def wait(self):
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request = time.time()

search_rate_limiter = RateLimiter(0.55)

# ---------------------------------------------------------------------------
# Networking / roll logic (runs on background threads)
# ---------------------------------------------------------------------------

def build_tribe_query(tribe):
    return f"t:{tribe} is:commander"

def fetch_commanders_for_tribe(tribe, log_fn):
    query = build_tribe_query(tribe)
    identity_counts = {}
    url = SCRYFALL_URL
    params = {"q": query}

    while url:
        search_rate_limiter.wait()
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        except Exception as e:
            log_fn(f"Network error: {e}", "err")
            break

        if response.status_code == 429:
            log_fn("Hit Scryfall's rate limit (429) - backing off 30s", "err")
            time.sleep(30)
            continue

        if response.status_code == 404:
            break

        if response.status_code != 200:
            log_fn(f"HTTP {response.status_code} for \"{query}\" - {response.text[:120]}", "err")
            break

        data = response.json()
        for card in data.get("data", []):
            ci = tuple(sorted(card.get("color_identity", [])))
            identity_counts[ci] = identity_counts.get(ci, 0) + 1

        if data.get("has_more") and data.get("next_page"):
            url = data["next_page"]
            params = None  
        else:
            url = None

    return identity_counts

def get_identity_counts_for_tribe(tribe, log_fn):
    with _cache_lock:
        cached = tribe_identity_cache.get(tribe)

    if cached and (time.time() - cached.get("timestamp", 0)) < TRIBE_CACHE_TTL_SECONDS:
        log_fn(f"[cache hit] {tribe} color identities loaded from local cache")
        return {tuple(k.split(",")) if k else (): v for k, v in cached["identities"].items()}

    log_fn(f"Searching commanders: {build_tribe_query(tribe)}")
    identity_counts = fetch_commanders_for_tribe(tribe, log_fn)

    with _cache_lock:
        tribe_identity_cache[tribe] = {
            "timestamp": time.time(),
            "identities": {",".join(k): v for k, v in identity_counts.items()},
        }
        save_json_file(TRIBE_CACHE_FILE, tribe_identity_cache)

    return identity_counts

def get_ci_weight(ci, weights_dict):
    if not ci:
        # Give Colorless the average weight of the 5 colors so it scales normally
        # with the rest of your stats without dragging the minimum weight down to 0.
        base_colors = ["W", "U", "B", "R", "G"]
        total = sum(weights_dict.get(c, 0) for c in base_colors)
        return total / 5.0
        
    # For colored identities, use the MAXIMUM weight of its constituent colors.
    # This prevents high-weight colors (like Green at 14) from sneaking through
    # in multi-color combinations if a lower-weight alternative exists in the tribe.
    return max(weights_dict.get(c, 0) for c in ci)

def pick_weighted_identity(eligible, log_fn):
    with _weights_lock:
        # Calculate current weights based on the MAX of individual colors
        weights_now = {ci: get_ci_weight(ci, color_weights) for ci in eligible}
        min_weight = min(weights_now.values())
        
        # Filter allowed by max difference of 3
        allowed = [ci for ci, w in weights_now.items() if w <= min_weight + 3]
        chosen = random.choice(allowed)
        
        # Increment each individual color by +1, completely skipping Colorless
        for color in chosen:
            color_weights[color] = color_weights.get(color, 0) + 1
        
        if len(chosen) > 0:  # Only save to JSON if it wasn't Colorless
            save_json_file(WEIGHTS_FILE, color_weights)

    # Format min_weight to 1 decimal place in the logs since Colorless can be a float
    log_fn(
        f"Weighting: {identity_name(chosen)} chosen (Lowest weight was {min_weight:.1f}, "
        f"{len(allowed)}/{len(eligible)} were within +3 threshold)"
    )
    return chosen

def find_one_valid_tribe(log_fn):
    start_time = time.time()
    while time.time() - start_time < ROLL_TIMEOUT_SECONDS:
        tribe = random.choice(TRIBES)
        with _cache_lock:
            is_cached_bust = tribe in invalid_tribe_cache
        if is_cached_bust:
            log_fn(f"[cache hit, skipping] {tribe} has no color identity with >=2 commanders")
            continue

        identity_counts = get_identity_counts_for_tribe(tribe, log_fn)
        eligible = {ci: count for ci, count in identity_counts.items() if count >= 2}

        if not eligible:
            log_fn(f"Bust: {tribe} has no color identity with >=2 commanders")
            with _cache_lock:
                invalid_tribe_cache.add(tribe)
            save_invalid_tribe(tribe)
            continue

        colors = pick_weighted_identity(eligible, log_fn)
        count = eligible[colors]
        log_fn(f"Hit! {tribe} ({identity_name(colors)}) -> {count} commanders", "ok")
        return (tribe, colors, count)
    return None

def batch_roll_worker(player_ids, num_rolls, result_queue):
    def log_fn(msg, kind=None):
        result_queue.put(("log", None, msg, kind))

    try:
        for pid in player_ids:
            found_list = []
            for _ in range(num_rolls):
                res = find_one_valid_tribe(log_fn)
                if res:
                    found_list.append(res)
            result_queue.put(("batch_done", pid, found_list))
    except Exception as e:
        log_fn(f"Worker thread crashed: {e}", "err")
    finally:
        # This ensures the UI ALWAYS unlocks, even if the thread errors out
        result_queue.put(("all_done", None, None))


# ---------------------------------------------------------------------------
# Slot reel widget
# ---------------------------------------------------------------------------

class SlotReel(tk.Canvas):
    ROW_H = 48
    VISIBLE_ROWS = 3

    def __init__(self, parent, width=230, default_fg=PARCHMENT, **kwargs):
        height = self.ROW_H * self.VISIBLE_ROWS
        super().__init__(parent, width=width, height=height, bg="#0C0C12",
                         highlightthickness=0, **kwargs)
        self.width_px = width
        self.default_fg = default_fg
        self.strip = []
        self.cyclic = True
        self.scroll_pos = 0.0
        self._render()

    def set_strip(self, items, cyclic):
        self.strip = items
        self.cyclic = cyclic
        self._render()

    def set_scroll(self, pos):
        self.scroll_pos = pos
        self._render()

    def _item_at(self, index):
        if not self.strip:
            return ("", None)
        if self.cyclic:
            return self.strip[index % len(self.strip)]
        if 0 <= index < len(self.strip):
            return self.strip[index]
        return ("", None)

    def _render(self):
        self.delete("all")
        row_h = self.ROW_H
        base_index = int(self.scroll_pos // row_h)
        offset = self.scroll_pos % row_h

        for visual_row in range(-1, self.VISIBLE_ROWS + 1):
            idx = base_index + visual_row
            text, bg = self._item_at(idx)
            y_top = visual_row * row_h - offset
            y_bottom = y_top + row_h
            if bg:
                self.create_rectangle(1, y_top, self.width_px - 1, y_bottom, fill=bg, outline="")
                fg = REEL_DARK_TEXT
            else:
                fg = self.default_fg
            if text:
                font_size = 12 if len(text) <= 14 else 10
                self.create_text(self.width_px / 2, (y_top + y_bottom) / 2, text=text,
                                 fill=fg, font=("Georgia", font_size, "bold"))

        self.create_rectangle(0, 0, self.width_px, row_h, fill="", outline="")
        self.create_rectangle(0, 0, self.width_px, row_h, stipple="gray50", fill=BG_VOID, outline="")
        self.create_rectangle(0, row_h * 2, self.width_px, row_h * 3, stipple="gray50", fill=BG_VOID, outline="")
        self.create_rectangle(2, row_h, self.width_px - 2, row_h * 2, outline=NEON_CYAN, width=2)


class SlotMachine(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style="Cabinet.TFrame", padding=16, **kwargs)

        self._bulb_ids = []
        self._bulb_phase = 0
        self.bulb_canvas = tk.Canvas(self, height=18, bg=BG_VOID, highlightthickness=0)
        self.bulb_canvas.pack(fill="x", pady=(0, 10))
        self._build_bulbs()

        reels_row = ttk.Frame(self, style="Cabinet.TFrame")
        reels_row.pack()

        left_col = ttk.Frame(reels_row, style="Cabinet.TFrame")
        left_col.grid(row=0, column=0, padx=(0, 6))
        ttk.Label(left_col, text="TRIBE", style="ReelLabel.TLabel").pack(pady=(0, 4))
        self.tribe_reel = SlotReel(left_col, width=230)
        self.tribe_reel.pack()

        arrow_col = ttk.Frame(reels_row, style="Cabinet.TFrame")
        arrow_col.grid(row=0, column=1, padx=4)
        ttk.Label(arrow_col, text="", style="Cabinet.TLabel").pack(pady=(0, 4))
        ttk.Label(arrow_col, text="\u25B6", style="Arrow.TLabel").pack(pady=(SlotReel.ROW_H - 10, 0))

        right_col = ttk.Frame(reels_row, style="Cabinet.TFrame")
        right_col.grid(row=0, column=2, padx=(6, 0))
        ttk.Label(right_col, text="COLOR IDENTITY", style="ReelLabel.TLabel").pack(pady=(0, 4))
        self.identity_reel = SlotReel(right_col, width=230)
        self.identity_reel.pack()

        bottom_bulbs = tk.Canvas(self, height=18, bg=BG_VOID, highlightthickness=0)
        bottom_bulbs.pack(fill="x", pady=(10, 0))
        self._bottom_bulb_canvas = bottom_bulbs
        self._bottom_bulb_ids = []
        self._build_bulbs(bottom_bulbs, self._bottom_bulb_ids)

        self._chase_bulbs()

    def _build_bulbs(self, canvas=None, store=None):
        canvas = canvas or self.bulb_canvas
        store = store if store is not None else self._bulb_ids
        canvas.delete("all")
        store.clear()
        canvas.update_idletasks()
        w = canvas.winfo_width() or 520
        spacing = 18
        count = max(4, w // spacing)
        for i in range(count):
            x = i * spacing + 10
            bid = canvas.create_oval(x - 4, 5, x + 4, 13, fill=GOLD, outline="")
            store.append(bid)

    def _chase_bulbs(self):
        for canvas, store, phase_attr in (
            (self.bulb_canvas, self._bulb_ids, "_bulb_phase"),
        ):
            n = len(store)
            if n:
                phase = getattr(self, phase_attr)
                for i, bid in enumerate(store):
                    lit = (i + phase) % 5 == 0
                    canvas.itemconfig(bid, fill=NEON_PINK if lit else GOLD)
                setattr(self, phase_attr, (phase + 1) % n)
        if self._bottom_bulb_ids:
            n = len(self._bottom_bulb_ids)
            phase = (self._bulb_phase + n // 2) % n
            for i, bid in enumerate(self._bottom_bulb_ids):
                lit = (i + phase) % 5 == 0
                self._bottom_bulb_canvas.itemconfig(bid, fill=NEON_CYAN if lit else GOLD)
        self.after(110, self._chase_bulbs)


# ---------------------------------------------------------------------------
# Player row widget
# ---------------------------------------------------------------------------

class PlayerRow(ttk.Frame):
    def __init__(self, parent, player_id, name, on_roll, on_remove):
        super().__init__(parent, style="Card.TFrame", padding=(14, 10))
        self.player_id = player_id
        self.on_roll = on_roll
        self.on_remove = on_remove
        self.results = []
        self.status = "idle"

        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(self, textvariable=self.name_var, style="Name.TEntry", width=14,
                               font=("Georgia", 12, "bold"))
        name_entry.grid(row=0, column=0, sticky="nw", padx=(0, 14))

        self.result_frame = ttk.Frame(self, style="Card.TFrame")
        self.result_frame.grid(row=0, column=1, sticky="w")
        self._render_result()

        self.status_label = ttk.Label(self, text="Not rolled", style="Status.TLabel")
        self.status_label.grid(row=0, column=2, sticky="ne", padx=(10, 10))

        self.roll_btn = ttk.Button(self, text="\U0001F3B0 Roll", style="Primary.TButton",
                                   command=lambda: self.on_roll(self.player_id))
        self.roll_btn.grid(row=0, column=3, sticky="ne", padx=(0, 6))

        remove_btn = ttk.Button(self, text="\u2715", style="Remove.TButton", width=3,
                                 command=lambda: self.on_remove(self.player_id))
        remove_btn.grid(row=0, column=4, sticky="ne")

        self.columnconfigure(1, weight=1)

    def _render_result(self):
        for w in self.result_frame.winfo_children():
            w.destroy()

        if self.status == "rolling":
            ttk.Label(self.result_frame, text="\U0001F3B2 spinning...",
                      style="Pending.TLabel").pack(side="left")
            return

        if not self.results:
            ttk.Label(self.result_frame, text="No tribe yet", style="Dim.TLabel").pack(side="left")
            return

        # Layout changes depending on if there is 1 result or multiple
        for tribe, colors, count in self.results:
            row_frame = tk.Frame(self.result_frame, bg=BG_CARD)
            row_frame.pack(side="top" if len(self.results) > 1 else "left", anchor="w", pady=2)

            guild = identity_name(colors)
            swatch = identity_color(colors)
            ttk.Label(row_frame, text=tribe, style="Tribe.TLabel").pack(side="left", padx=(0, 6))
            guild_badge = tk.Label(row_frame, text=f" {guild} ", fg=REEL_DARK_TEXT, bg=swatch,
                                   font=("Segoe UI", 9, "bold"))
            guild_badge.pack(side="left", padx=(0, 8))
            badge = tk.Label(row_frame, text=f" {count} cmdrs ",
                             fg=GREEN_OK, bg=BG_CARD_2, font=("Segoe UI", 9, "bold"))
            badge.pack(side="left")

    def set_status(self, status):
        self.status = status
        if status == "rolling":
            self.status_label.config(text="Rolling...", style="StatusActive.TLabel")
            self.roll_btn.config(state="disabled")
        else:
            self.status_label.config(
                text="Locked in" if self.results else "Not rolled",
                style="Status.TLabel",
            )
        self._render_result()

    def set_results(self, results_list):
        self.results = results_list
        self.status = "idle"
        self.status_label.config(text="Locked in", style="Status.TLabel")
        self.roll_btn.config(text="\U0001F3B0 Reroll", state="normal")
        self._render_result()

    def set_timeout(self):
        self.status = "idle"
        self.status_label.config(text="No payout - try again", style="StatusActive.TLabel")
        self.roll_btn.config(state="normal")
        self._render_result()

    def set_enabled(self, enabled):
        if self.status != "rolling":
            self.roll_btn.config(state="normal" if enabled else "disabled")

    @property
    def name(self):
        return self.name_var.get()


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class WheelOfTribesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wheel of Tribes \u2660 Vegas Edition")
        self.root.configure(bg=BG_VOID)
        self.root.geometry("820x840")
        self.root.minsize(700, 660)

        self.players = []
        self.player_id_seq = 1
        self.result_queue = queue.Queue()
        self.is_any_rolling = False
        self._spinning = False

        self._build_style()
        self._build_layout()

        self.root.after(50, self._poll_queue)
        self._setup_table()
        self._log(
            f"Loaded {len(invalid_tribe_cache)} known bust tribes and "
            f"{len(color_weights)} color-weight entries from disk."
        )

    # -- styling -----------------------------------------------------------

    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG_VOID)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("Cabinet.TFrame", background=BG_VOID)
        style.configure("TLabel", background=BG_VOID, foreground=PARCHMENT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT,
                         font=("Impact", 30))
        style.configure("Subtitle.TLabel", background=BG_VOID, foreground=NEON_CYAN,
                         font=("Segoe UI", 10, "italic"))
        style.configure("StageName.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT,
                         font=("Georgia", 16, "bold"))
        style.configure("StageResult.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM,
                         font=("Segoe UI", 10))
        style.configure("ReelLabel.TLabel", background=BG_VOID, foreground=GOLD,
                         font=("Segoe UI", 9, "bold"))
        style.configure("Arrow.TLabel", background=BG_VOID, foreground=NEON_CYAN, font=("Segoe UI", 14, "bold"))
        style.configure("Dim.TLabel", background=BG_CARD, foreground=PARCHMENT_DIM)
        style.configure("Tribe.TLabel", background=BG_CARD, foreground=PARCHMENT,
                         font=("Segoe UI", 11, "bold"))
        style.configure("Pending.TLabel", background=BG_CARD, foreground=NEON_PINK)
        style.configure("Status.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM, font=("Segoe UI", 9))
        style.configure("StatusActive.TLabel", background=BG_VOID, foreground=NEON_PINK, font=("Segoe UI", 9, "bold"))

        style.configure("Primary.TButton", background="#7A1530", foreground=GOLD_BRIGHT,
                         font=("Segoe UI", 9, "bold"), padding=6, borderwidth=1)
        style.map("Primary.TButton", background=[("active", "#9c1c3d")])
        style.configure("Remove.TButton", background=BG_CARD, foreground=RED_ERR, padding=4)
        style.map("Remove.TButton", background=[("active", "#3a2230")])
        style.configure("Setup.TButton", background="#1D3327", foreground=GOLD_BRIGHT,
                         font=("Segoe UI", 9, "bold"), padding=8)
        style.map("Setup.TButton", background=[("active", BG_CARD)])

        style.configure("Name.TEntry", fieldbackground=BG_CARD, foreground=PARCHMENT,
                         insertcolor=PARCHMENT, borderwidth=0)
        style.configure("TSpinbox", fieldbackground=BG_CARD, foreground=PARCHMENT,
                         background=BG_CARD, arrowcolor=GOLD)

    # -- layout --------------------------------------------------------------

    def _build_layout(self):
        wrap = ttk.Frame(self.root, padding=24)
        wrap.pack(fill="both", expand=True)

        ttk.Label(wrap, text="\u2666 WHEEL OF TRIBES \u2666", style="Title.TLabel").pack()
        ttk.Label(wrap, text="No purchase necessary. Scryfall guarantees the payout is real.",
                  style="Subtitle.TLabel").pack(pady=(0, 16))

        setup_row = ttk.Frame(wrap)
        setup_row.pack(pady=(0, 16))
        ttk.Label(setup_row, text="Players at the Table").pack(side="left", padx=(0, 8))
        self.player_count_var = tk.IntVar(value=2)
        spin = ttk.Spinbox(setup_row, from_=1, to=8, textvariable=self.player_count_var, width=4,
                            justify="center")
        spin.pack(side="left", padx=(0, 10))
        ttk.Button(setup_row, text="\u2666 Open Table \u2666", style="Setup.TButton",
                   command=self._setup_table).pack(side="left")
        
        ttk.Button(setup_row, text="\U0001F3B2 Roll 2 for All", style="Setup.TButton",
                   command=self._roll_two_for_all).pack(side="left", padx=(10, 0))

        stage = ttk.Frame(wrap)
        stage.pack(pady=(0, 20))
        self.slot_machine = SlotMachine(stage)
        self.slot_machine.pack()

        self.stage_name = ttk.Label(stage, text="Take a seat and place your roll", style="StageName.TLabel")
        self.stage_name.pack(pady=(14, 2))
        self.stage_result = ttk.Label(stage, text="", style="StageResult.TLabel")
        self.stage_result.pack()

        self.players_container = ttk.Frame(wrap)
        self.players_container.pack(fill="x", pady=(8, 16))

        log_header = ttk.Frame(wrap)
        log_header.pack(fill="x")
        ttk.Label(log_header, text="Pit Boss Log", style="Subtitle.TLabel").pack(side="left")

        log_frame = tk.Frame(wrap, bg="#0E0A18", highlightbackground=LINE, highlightthickness=1)
        log_frame.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text = tk.Text(log_frame, height=8, bg="#0E0A18", fg="#9C92B5",
                                 insertbackground="#9C92B5", relief="flat", wrap="word",
                                 font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True, padx=8, pady=6)
        self.log_text.tag_config("err", foreground=RED_ERR)
        self.log_text.tag_config("ok", foreground=GREEN_OK)
        self.log_text.config(state="disabled")

    # -- logging -------------------------------------------------------------

    def _log(self, text, kind=None):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n", kind)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # -- player table management ---------------------------------------------

    def _setup_table(self):
        if self.is_any_rolling:
            return
        for row in self.players:
            row.destroy()
        self.players = []
        self.player_id_seq = 1

        target = self.player_count_var.get()
        for i in range(target):
            self._add_player_row(f"Player {i + 1}")

        self._log(f"Table opened with {target} player{'s' if target != 1 else ''}.")

    def _add_player_row(self, name):
        pid = self.player_id_seq
        self.player_id_seq += 1
        row = PlayerRow(self.players_container, pid, name, self._roll_for_player, self._remove_player)
        row.pack(fill="x", pady=5)
        self.players.append(row)

    def _remove_player(self, player_id):
        if self.is_any_rolling:
            return
        row = self._get_row(player_id)
        if row:
            row.destroy()
            self.players.remove(row)

    def _get_row(self, player_id):
        return next((r for r in self.players if r.player_id == player_id), None)

    # -- rolling logic ---------------------------------------------------------

    def _roll_for_player(self, player_id):
        if self.is_any_rolling:
            return
        row = self._get_row(player_id)
        if not row:
            return

        self.is_any_rolling = True
        row.set_status("rolling")
        for r in self.players:
            r.set_enabled(False)

        self.stage_name.config(text=f"{row.name} is spinning...")
        threading.Thread(target=batch_roll_worker, args=([player_id], 1, self.result_queue), daemon=True).start()
        self._start_reels()
        
    def _roll_two_for_all(self):
        if self.is_any_rolling or not self.players:
            return
            
        self.is_any_rolling = True
        for r in self.players:
            r.set_status("rolling")
            r.set_enabled(False)

        self.stage_name.config(text="Rolling 2 for everyone! (Please wait...)")
        
        player_ids = [p.player_id for p in self.players]
        threading.Thread(target=batch_roll_worker, args=(player_ids, 2, self.result_queue), daemon=True).start()
        self._start_reels()

    # -- wheel animations and event loops --------------------------------------
    
    def _start_reels(self):
        self._spinning = True
        self._spin_step()
        
    def _spin_step(self):
        if not self._spinning:
            return
        fake_tribes = [(random.choice(TRIBES), None) for _ in range(5)]
        fake_ids = [random.choice(ALL_IDENTITIES) for _ in range(5)]
        self.slot_machine.tribe_reel.set_strip(fake_tribes, True)
        self.slot_machine.identity_reel.set_strip(fake_ids, True)
        
        self.slot_machine.tribe_reel.set_scroll(self.slot_machine.tribe_reel.scroll_pos + 12)
        self.slot_machine.identity_reel.set_scroll(self.slot_machine.identity_reel.scroll_pos + 16)
        
        self.root.after(30, self._spin_step)

    def _poll_queue(self):
        while not self.result_queue.empty():
            item = self.result_queue.get()
            msg_type = item[0]
            pid = item[1]
            payload = item[2]
            
            if msg_type == "log":
                kind = item[3] if len(item) > 3 else None
                self._log(payload, kind)
                
            elif msg_type == "batch_done":
                row = self._get_row(pid)
                if row:
                    if payload:
                        row.set_results(payload)
                        last_tribe, last_colors, _ = payload[-1]
                        self.slot_machine.tribe_reel.set_strip([(last_tribe, None)], False)
                        self.slot_machine.tribe_reel.set_scroll(0)
                        
                        id_name = identity_name(last_colors)
                        id_col = identity_color(last_colors)
                        self.slot_machine.identity_reel.set_strip([(id_name, id_col)], False)
                        self.slot_machine.identity_reel.set_scroll(0)
                        self.stage_name.config(text=f"{row.name} locked in!")
                    else:
                        row.set_timeout()
                        self.stage_name.config(text="Bust! Try again.")
                        
            elif msg_type == "all_done":
                self.is_any_rolling = False
                self._spinning = False
                for r in self.players:
                    r.set_enabled(True)
                if len(self.players) > 1:
                    self.stage_name.config(text="All rolls complete!")
                    
        self.root.after(50, self._poll_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = WheelOfTribesApp(root)
    root.mainloop()