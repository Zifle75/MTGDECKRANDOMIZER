"""
Wheel of Tribes (Vegas Edition)
A desktop Commander tribal randomizer: set up your table, roll each player a
tribe + color identity, watch the wheel spin and land on it, reroll anyone
who wants a new fate.

Requires: requests   (pip install requests)
Run:      python wheel_of_tribes.py
"""

import math
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
INVALID_FILE = "invalid_combos.txt"

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

# Color identity -> common Magic name (guilds / wedges / shards)
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
}

COLOR_HEX = {
    "W": "#F2E9C9",
    "U": "#33B5E5",
    "B": "#B07CFF",
    "R": "#FF4D4D",
    "G": "#4BD17B",
}

# ---- Vegas theme palette ---------------------------------------------------
BG_VOID = "#0A0A0F"          # near-black casino floor
BG_CARD = "#14241C"          # felt-table green-black
BG_CARD_2 = "#1D3327"        # felt highlight
LINE = "#3A2A12"             # bronze divider
PARCHMENT = "#F4E9D8"
PARCHMENT_DIM = "#B9A98A"
GOLD = "#FFD447"
GOLD_BRIGHT = "#FFE98A"
NEON_PINK = "#FF2DA0"
NEON_CYAN = "#27E6E6"
GREEN_OK = "#5CFF9D"
RED_ERR = "#FF5D5D"

ROLL_TIMEOUT_SECONDS = 10
HEADERS = {
    "User-Agent": "WheelOfTribesApp/1.0",
    "Accept": "application/json",
}


def identity_name(colors):
    key = tuple(sorted(colors))
    return COLOR_IDENTITY_NAMES.get(key, "/".join(key) if key else "Colorless")


# ---------------------------------------------------------------------------
# Invalid combo cache (persisted to disk, just like the original script)
# ---------------------------------------------------------------------------

def load_invalid_combos():
    if not os.path.exists(INVALID_FILE):
        return set()
    with open(INVALID_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())


def save_invalid_combo(combo_key):
    with open(INVALID_FILE, "a") as f:
        f.write(combo_key + "\n")


invalid_cache = load_invalid_combos()
_cache_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Networking / roll logic (runs on background threads)
# ---------------------------------------------------------------------------


def build_query(tribe, colors):
    color_str = "".join(colors)
    return f"t:{tribe} id={color_str} is:commander"


def fetch_count(query, log_fn):
    try:
        response = requests.get(
            SCRYFALL_URL,
            params={"q": query},
            headers=HEADERS,
            timeout=10,
        )
        if response.status_code != 200:
            log_fn(f"HTTP {response.status_code} for \"{query}\" - {response.text[:120]}", "err")
            return 0
        data = response.json()
        return data.get("total_cards", 0)
    except Exception as e:
        log_fn(f"Network error: {e}", "err")
        return 0


def random_color_identity():
    count = random.randint(1, 3)
    return tuple(sorted(random.sample(COLORS, count)))


def roll_worker(player_id, result_queue):
    """Runs on a background thread. Pushes events to result_queue for the UI thread to consume."""

    def log_fn(msg, kind=None):
        result_queue.put(("log", player_id, msg, kind))

    start_time = time.time()
    found = None

    while time.time() - start_time < ROLL_TIMEOUT_SECONDS:
        tribe = random.choice(TRIBES)
        colors = random_color_identity()
        key = f"{tribe}|{''.join(colors)}"

        with _cache_lock:
            is_cached = key in invalid_cache

        if is_cached:
            log_fn(f"[cache hit, skipping] {key}")
            continue

        query = build_query(tribe, colors)
        log_fn(f"Querying {query}")
        count = fetch_count(query, log_fn)

        if count >= 3:
            log_fn(f"Hit! {tribe} ({identity_name(colors)}) -> {count} commanders", "ok")
            found = (tribe, colors, count)
            break
        else:
            log_fn(f"Bust: {key} ({count})")
            with _cache_lock:
                invalid_cache.add(key)
            save_invalid_combo(key)

    if found:
        result_queue.put(("found", player_id, found[0], found[1], found[2]))
    else:
        result_queue.put(("timeout", player_id, None, None, None))


# ---------------------------------------------------------------------------
# Wheel widget
# ---------------------------------------------------------------------------

class WheelCanvas(tk.Canvas):
    def __init__(self, parent, size=340, **kwargs):
        super().__init__(parent, width=size, height=size, bg=BG_VOID,
                          highlightthickness=0, **kwargs)
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        self.r = size / 2 - 24
        self.rotation = 0.0
        self.n = len(TRIBES)
        self.palette = [COLOR_HEX["W"], COLOR_HEX["U"], COLOR_HEX["B"], COLOR_HEX["R"], COLOR_HEX["G"]]
        self._bulb_phase = 0
        self._bulb_ids = []
        self._draw()
        self._draw_bulbs()
        self._draw_pointer()
        self._chase_bulbs()

    def _draw(self):
        self.delete("wedge")
        seg = 360 / self.n
        bbox = (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)
        for i in range(self.n):
            start = (self.rotation + i * seg) % 360
            color = self.palette[i % len(self.palette)]
            self.create_arc(
                *bbox, start=start, extent=seg,
                fill=color, outline="#0A0A0F", width=2,
                style=tk.PIESLICE, tags="wedge",
            )
            mid_deg = start + seg / 2
            mid_rad = math.radians(mid_deg)
            tx = self.cx + (self.r * 0.62) * math.cos(mid_rad)
            ty = self.cy - (self.r * 0.62) * math.sin(mid_rad)
            text_angle = mid_deg if -90 <= ((mid_deg + 90) % 360) - 90 <= 90 else mid_deg + 180
            try:
                self.create_text(
                    tx, ty, text=TRIBES[i], fill="#160F26",
                    font=("Georgia", 9, "bold"), angle=text_angle, tags="wedge",
                )
            except tk.TclError:
                self.create_text(tx, ty, text=TRIBES[i], fill="#160F26",
                                  font=("Georgia", 8, "bold"), tags="wedge")
        self.tag_raise("bulb")
        self.tag_raise("pointer")
        self.tag_raise("hub")

    def _draw_bulbs(self):
        self.delete("bulb")
        bulb_count = 24
        ring_r = self.r + 12
        self._bulb_ids = []
        for i in range(bulb_count):
            ang = math.radians(i * (360 / bulb_count))
            bx = self.cx + ring_r * math.cos(ang)
            by = self.cy - ring_r * math.sin(ang)
            bid = self.create_oval(bx - 4, by - 4, bx + 4, by + 4,
                                    fill=GOLD, outline="", tags="bulb")
            self._bulb_ids.append(bid)

    def _chase_bulbs(self):
        n = len(self._bulb_ids)
        if n:
            for i, bid in enumerate(self._bulb_ids):
                lit = (i + self._bulb_phase) % 6 == 0
                self.itemconfig(bid, fill=NEON_PINK if lit else GOLD)
            self._bulb_phase = (self._bulb_phase + 1) % n
        self.after(120, self._chase_bulbs)

    def _draw_pointer(self):
        self.create_polygon(
            self.cx - 13, 6, self.cx + 13, 6, self.cx, 30,
            fill=NEON_CYAN, outline=GOLD_BRIGHT, width=1, tags="pointer",
        )
        self.create_oval(
            self.cx - 42, self.cy - 42, self.cx + 42, self.cy + 42,
            fill="#160F26", outline=GOLD, width=3, tags="hub",
        )
        self.create_text(self.cx, self.cy, text="\u2660", font=("Georgia", 24), fill=GOLD_BRIGHT, tags="hub")

    def set_rotation(self, deg):
        self.rotation = deg % 360
        self._draw()


# ---------------------------------------------------------------------------
# Player row widget
# ---------------------------------------------------------------------------

class PlayerRow(ttk.Frame):
    def __init__(self, parent, player_id, name, on_roll, on_remove):
        super().__init__(parent, style="Card.TFrame", padding=(14, 10))
        self.player_id = player_id
        self.on_roll = on_roll
        self.on_remove = on_remove
        self.result = None
        self.status = "idle"

        self.name_var = tk.StringVar(value=name)
        name_entry = ttk.Entry(self, textvariable=self.name_var, style="Name.TEntry", width=14,
                                font=("Georgia", 12, "bold"))
        name_entry.grid(row=0, column=0, sticky="w", padx=(0, 14))

        self.result_frame = ttk.Frame(self, style="Card.TFrame")
        self.result_frame.grid(row=0, column=1, sticky="w")
        self._render_result()

        self.status_label = ttk.Label(self, text="Not rolled", style="Status.TLabel")
        self.status_label.grid(row=0, column=2, padx=(10, 10))

        self.roll_btn = ttk.Button(self, text="\U0001F3B0 Roll", style="Primary.TButton",
                                    command=lambda: self.on_roll(self.player_id))
        self.roll_btn.grid(row=0, column=3, padx=(0, 6))

        remove_btn = ttk.Button(self, text="\u2715", style="Remove.TButton", width=3,
                                 command=lambda: self.on_remove(self.player_id))
        remove_btn.grid(row=0, column=4)

        self.columnconfigure(1, weight=1)

    def _render_result(self):
        for w in self.result_frame.winfo_children():
            w.destroy()

        if self.status == "rolling":
            ttk.Label(self.result_frame, text="\U0001F3B2 spinning...",
                      style="Pending.TLabel").pack(side="left")
            return

        if not self.result:
            ttk.Label(self.result_frame, text="No tribe yet", style="Dim.TLabel").pack(side="left")
            return

        tribe, colors, count = self.result
        guild = identity_name(colors)
        ttk.Label(self.result_frame, text=tribe, style="Tribe.TLabel").pack(side="left", padx=(0, 6))
        guild_badge = tk.Label(self.result_frame, text=f" {guild} ", fg="#0A0A0F", bg=GOLD,
                                font=("Segoe UI", 9, "bold"))
        guild_badge.pack(side="left", padx=(0, 8))
        badge = tk.Label(self.result_frame, text=f" {count} commanders ",
                          fg=GREEN_OK, bg=BG_CARD_2, font=("Segoe UI", 9, "bold"))
        badge.pack(side="left")

    def set_status(self, status):
        self.status = status
        if status == "rolling":
            self.status_label.config(text="Rolling...", style="StatusActive.TLabel")
            self.roll_btn.config(state="disabled")
        else:
            self.status_label.config(
                text="Locked in" if self.result else "Not rolled",
                style="Status.TLabel",
            )
        self._render_result()

    def set_result(self, tribe, colors, count):
        self.result = (tribe, colors, count)
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
        self.root.geometry("780x800")
        self.root.minsize(660, 620)

        self.players = []
        self.player_id_seq = 1
        self.result_queue = queue.Queue()
        self.is_any_rolling = False
        self.active_player_id = None
        self._flash_job = None
        self._spinning = False

        self._build_style()
        self._build_layout()

        self.root.after(50, self._poll_queue)
        self._setup_table()
        self._log(f"Loaded {len(invalid_cache)} known bust combos from {INVALID_FILE}.")

    # -- styling -----------------------------------------------------------

    def _build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG_VOID)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG_VOID, foreground=PARCHMENT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT,
                         font=("Impact", 30))
        style.configure("Subtitle.TLabel", background=BG_VOID, foreground=NEON_CYAN,
                         font=("Segoe UI", 10, "italic"))
        style.configure("StageName.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT,
                         font=("Georgia", 16, "bold"))
        style.configure("StageResult.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM,
                         font=("Segoe UI", 10))
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

        stage = ttk.Frame(wrap)
        stage.pack(pady=(0, 20))
        self.wheel = WheelCanvas(stage)
        self.wheel.pack()

        self.stage_name = ttk.Label(stage, text="Take a seat and place your roll", style="StageName.TLabel")
        self.stage_name.pack(pady=(10, 2))
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
        row = next((r for r in self.players if r.player_id == player_id), None)
        if row:
            row.destroy()
            self.players.remove(row)

    def _get_row(self, player_id):
        return next((r for r in self.players if r.player_id == player_id), None)

    # -- rolling ---------------------------------------------------------------

    def _roll_for_player(self, player_id):
        if self.is_any_rolling:
            return
        row = self._get_row(player_id)
        if not row:
            return

        self.is_any_rolling = True
        self.active_player_id = player_id
        row.set_status("rolling")
        for r in self.players:
            r.set_enabled(False)

        self.stage_name.config(text=f"{row.name} is pulling the lever...", foreground=GOLD_BRIGHT)
        self.stage_result.config(text="")
        self._start_indefinite_spin()

        thread = threading.Thread(target=roll_worker, args=(player_id, self.result_queue), daemon=True)
        thread.start()

    def _start_indefinite_spin(self):
        self._spinning = True
        self._spin_tick()

    def _spin_tick(self):
        if not self._spinning:
            return
        self.wheel.set_rotation(self.wheel.rotation + 14)
        self.root.after(40, self._spin_tick)

    def _stop_indefinite_spin(self):
        self._spinning = False

    def _land_wheel_on(self, tribe, on_done):
        n = len(TRIBES)
        idx = TRIBES.index(tribe)
        seg = 360 / n
        seg_center = idx * seg + seg / 2
        current = self.wheel.rotation % 360

        target_static = (90 - seg_center) % 360
        delta = (target_static - current) % 360
        extra_spins = 5 * 360
        total_delta = extra_spins + delta

        start_rot = self.wheel.rotation
        duration_ms = 3200
        start_time = time.time()

        def ease_out_cubic(t):
            return 1 - pow(1 - t, 3)

        def frame():
            elapsed = (time.time() - start_time) * 1000
            t = min(1.0, elapsed / duration_ms)
            eased = ease_out_cubic(t)
            self.wheel.set_rotation(start_rot + total_delta * eased)
            if t < 1.0:
                self.root.after(16, frame)
            else:
                on_done()

        frame()

    def _flash_jackpot(self, times_left=8):
        colors = [GOLD_BRIGHT, NEON_PINK]
        self.stage_name.config(foreground=colors[times_left % 2])
        if times_left > 0:
            self._flash_job = self.root.after(140, lambda: self._flash_jackpot(times_left - 1))
        else:
            self.stage_name.config(foreground=GOLD_BRIGHT)

    # -- queue polling (UI-thread-safe updates from worker threads) ----------

    def _poll_queue(self):
        try:
            while True:
                event = self.result_queue.get_nowait()
                kind = event[0]
                player_id = event[1]

                if kind == "log":
                    _, _, msg, tag = event
                    self._log(msg, tag)

                elif kind == "found":
                    _, _, tribe, colors, count = event
                    self._stop_indefinite_spin()

                    def on_landed(tribe=tribe, colors=colors, count=count, player_id=player_id):
                        row = self._get_row(player_id)
                        guild = identity_name(colors)
                        if row:
                            row.set_result(tribe, colors, count)
                            self.stage_name.config(text=f"\U0001F4B0 JACKPOT \u2014 {row.name}: {tribe}")
                            self.stage_result.config(
                                text=f"{guild}  \u2014  {count} legal commanders on the table"
                            )
                            self._flash_jackpot()
                        self._finish_roll()

                    self._land_wheel_on(tribe, on_landed)

                elif kind == "timeout":
                    self._stop_indefinite_spin()
                    row = self._get_row(player_id)
                    if row:
                        row.set_timeout()
                        self.stage_name.config(text=f"House wins \u2014 no hit for {row.name}", foreground=GOLD_BRIGHT)
                        self.stage_result.config(text="The wheel ran out of time. Pull again.")
                    self._finish_roll()

        except queue.Empty:
            pass

        self.root.after(50, self._poll_queue)

    def _finish_roll(self):
        self.is_any_rolling = False
        self.active_player_id = None
        for r in self.players:
            r.set_enabled(True)

    def _log(self, msg, tag=None):
        self.log_text.config(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n", tag or "")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = WheelOfTribesApp(root)
    root.mainloop()