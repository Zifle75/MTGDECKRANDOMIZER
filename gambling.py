"""
Wheel of Tribes
A desktop Commander tribal randomizer: set up your table, roll each player a
tribe + color identity, watch the wheel spin and land on it, reroll anyone
who wants a new fate.

Requires: requests   (pip install requests)
Run:      python wheel_of_tribes.py
"""

import math
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

COLORS = ["W", "U", "B", "R", "G"]

TRIBES = [
    "Elf", "Zombie", "Dragon", "Goblin", "Angel", "Wizard", "Warrior",
    "Cleric", "Shaman", "Spirit", "Vampire", "Knight", "Beast", "Human",
    "Merfolk", "Cat", "Dog", "Snake", "Hydra", "Giant", "Rogue",
    "Insect", "Spider", "Frog",
]

COLOR_HEX = {
    "W": "#F2E9C9",
    "U": "#2C7FC1",
    "B": "#7A4FC2",
    "R": "#D9533A",
    "G": "#3F8F5B",
}

# theme palette
BG_VOID = "#120E1A"
BG_CARD = "#1D1730"
BG_CARD_2 = "#241C3D"
LINE = "#352B53"
PARCHMENT = "#ECE3C8"
PARCHMENT_DIM = "#B8AE92"
GOLD = "#C9A84C"
GOLD_BRIGHT = "#E8C766"
GREEN_OK = "#8FD9A6"
RED_ERR = "#C26A5C"

ROLL_TIMEOUT_SECONDS = 10
HEADERS = {
    "User-Agent": "WheelOfTribesApp/1.0",
    "Accept": "application/json",
}

# ---------------------------------------------------------------------------
# Networking / roll logic (runs on background threads)
# ---------------------------------------------------------------------------

invalid_cache = set()  # shared across the whole app session


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

        if key in invalid_cache:
            log_fn(f"[cache hit] {key}")
            continue

        query = build_query(tribe, colors)
        log_fn(f"Querying {query}")
        count = fetch_count(query, log_fn)

        if count >= 3:
            log_fn(f"Valid: {tribe} {''.join(colors)} -> {count} commanders", "ok")
            found = (tribe, colors, count)
            break
        else:
            log_fn(f"Invalid: {key} ({count})")
            invalid_cache.add(key)

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
        self.r = size / 2 - 18
        self.rotation = 0.0
        self.n = len(TRIBES)
        self.palette = [COLOR_HEX["W"], COLOR_HEX["U"], COLOR_HEX["B"], COLOR_HEX["R"], COLOR_HEX["G"]]
        self._draw()
        self._draw_pointer()

    def _draw(self):
        self.delete("wedge")
        seg = 360 / self.n
        bbox = (self.cx - self.r, self.cy - self.r, self.cx + self.r, self.cy + self.r)
        for i in range(self.n):
            start = (self.rotation + i * seg) % 360
            color = self.palette[i % len(self.palette)]
            self.create_arc(
                *bbox, start=start, extent=seg,
                fill=color, outline=BG_VOID, width=2,
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
                # older Tk without angle support on create_text
                self.create_text(tx, ty, text=TRIBES[i], fill="#160F26",
                                  font=("Georgia", 8, "bold"), tags="wedge")

    def _draw_pointer(self):
        self.create_polygon(
            self.cx - 12, 4, self.cx + 12, 4, self.cx, 26,
            fill=GOLD_BRIGHT, outline="", tags="pointer",
        )
        self.create_oval(
            self.cx - 40, self.cy - 40, self.cx + 40, self.cy + 40,
            fill="#160F26", outline=GOLD, width=2, tags="hub",
        )
        self.create_text(self.cx, self.cy, text="\U0001F0CF", font=("Segoe UI Emoji", 20), tags="hub")

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
        name_entry = ttk.Entry(self, textvariable=self.name_var, style="Name.TEntry", width=14, font=("Georgia", 12, "bold"))
        name_entry.grid(row=0, column=0, sticky="w", padx=(0, 14))

        self.result_frame = ttk.Frame(self, style="Card.TFrame")
        self.result_frame.grid(row=0, column=1, sticky="w")
        self._render_result()

        self.status_label = ttk.Label(self, text="Not rolled", style="Status.TLabel")
        self.status_label.grid(row=0, column=2, padx=(10, 10))

        self.roll_btn = ttk.Button(self, text="Roll", style="Primary.TButton",
                                    command=lambda: self.on_roll(self.player_id))
        self.roll_btn.grid(row=0, column=3, padx=(0, 6))

        remove_btn = ttk.Button(self, text="✕", style="Remove.TButton", width=3,
                                 command=lambda: self.on_remove(self.player_id))
        remove_btn.grid(row=0, column=4)

        self.columnconfigure(1, weight=1)

    def _render_result(self):
        for w in self.result_frame.winfo_children():
            w.destroy()

        if self.status == "rolling":
            ttk.Label(self.result_frame, text="Consulting the wheel...",
                      style="Pending.TLabel").pack(side="left")
            return

        if not self.result:
            ttk.Label(self.result_frame, text="No tribe yet", style="Dim.TLabel").pack(side="left")
            return

        tribe, colors, count = self.result
        ttk.Label(self.result_frame, text=tribe, style="Tribe.TLabel").pack(side="left", padx=(0, 6))
        for c in colors:
            pip = tk.Label(self.result_frame, text="\u25CF", fg=COLOR_HEX[c], bg=BG_CARD,
                            font=("Arial", 12))
            pip.pack(side="left", padx=1)
        badge = tk.Label(self.result_frame, text=f" {count} commanders ",
                          fg=GREEN_OK, bg=BG_CARD_2, font=("Segoe UI", 9, "bold"))
        badge.pack(side="left", padx=(8, 0))

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
        self.roll_btn.config(text="Reroll", state="normal")
        self._render_result()

    def set_timeout(self):
        self.status = "idle"
        self.status_label.config(text="Timed out - try again", style="StatusActive.TLabel")
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
        self.root.title("Wheel of Tribes")
        self.root.configure(bg=BG_VOID)
        self.root.geometry("760x760")
        self.root.minsize(640, 600)

        self.players = []          # list of PlayerRow
        self.player_id_seq = 1
        self.result_queue = queue.Queue()
        self.is_any_rolling = False
        self.active_player_id = None

        self._build_style()
        self._build_layout()

        self.root.after(50, self._poll_queue)
        self._setup_table()

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
                         font=("Georgia", 24, "bold"))
        style.configure("Subtitle.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM,
                         font=("Segoe UI", 10, "italic"))
        style.configure("StageName.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT,
                         font=("Georgia", 14, "bold"))
        style.configure("StageResult.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM,
                         font=("Segoe UI", 10))
        style.configure("Dim.TLabel", background=BG_CARD, foreground=PARCHMENT_DIM)
        style.configure("Tribe.TLabel", background=BG_CARD, foreground=PARCHMENT,
                         font=("Segoe UI", 11, "bold"))
        style.configure("Pending.TLabel", background=BG_CARD, foreground=GOLD_BRIGHT)
        style.configure("Status.TLabel", background=BG_VOID, foreground=PARCHMENT_DIM, font=("Segoe UI", 9))
        style.configure("StatusActive.TLabel", background=BG_VOID, foreground=GOLD_BRIGHT, font=("Segoe UI", 9, "bold"))

        style.configure("Primary.TButton", background=BG_CARD_2, foreground=GOLD_BRIGHT,
                         font=("Segoe UI", 9, "bold"), padding=6, borderwidth=1)
        style.map("Primary.TButton", background=[("active", "#3a2c63")])
        style.configure("Remove.TButton", background=BG_CARD, foreground=RED_ERR, padding=4)
        style.map("Remove.TButton", background=[("active", "#3a2230")])
        style.configure("Setup.TButton", background=BG_CARD_2, foreground=PARCHMENT,
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

        ttk.Label(wrap, text="Wheel of Tribes", style="Title.TLabel").pack()
        ttk.Label(wrap, text="Fate picks your tribe. Scryfall confirms it's playable.",
                  style="Subtitle.TLabel").pack(pady=(0, 16))

        # setup row
        setup_row = ttk.Frame(wrap)
        setup_row.pack(pady=(0, 16))
        ttk.Label(setup_row, text="Players").pack(side="left", padx=(0, 8))
        self.player_count_var = tk.IntVar(value=2)
        spin = ttk.Spinbox(setup_row, from_=1, to=8, textvariable=self.player_count_var, width=4,
                            justify="center")
        spin.pack(side="left", padx=(0, 10))
        ttk.Button(setup_row, text="Set Up Table", style="Setup.TButton",
                   command=self._setup_table).pack(side="left")

        # wheel stage
        stage = ttk.Frame(wrap)
        stage.pack(pady=(0, 20))
        self.wheel = WheelCanvas(stage)
        self.wheel.pack()

        self.stage_name = ttk.Label(stage, text="Add players, then roll one", style="StageName.TLabel")
        self.stage_name.pack(pady=(10, 2))
        self.stage_result = ttk.Label(stage, text="", style="StageResult.TLabel")
        self.stage_result.pack()

        # players list
        self.players_container = ttk.Frame(wrap)
        self.players_container.pack(fill="x", pady=(8, 16))

        # log
        log_header = ttk.Frame(wrap)
        log_header.pack(fill="x")
        ttk.Label(log_header, text="Roll log", style="Subtitle.TLabel").pack(side="left")

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

        self._log(f"Table set with {target} player{'s' if target != 1 else ''}.")

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

        self.stage_name.config(text=f"{row.name} is rolling...")
        self.stage_result.config(text="")
        self._start_indefinite_spin()

        thread = threading.Thread(target=roll_worker, args=(player_id, self.result_queue), daemon=True)
        thread.start()

    def _start_indefinite_spin(self):
        self._spinning = True
        self._spin_tick()

    def _spin_tick(self):
        if not getattr(self, "_spinning", False):
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

        # tkinter arcs go counter-clockwise from 0deg at 3-o'clock; pointer sits at top (90deg).
        target_static = (90 - seg_center) % 360
        delta = (target_static - current) % 360
        extra_spins = 5 * 360
        total_delta = extra_spins + delta

        start_rot = self.wheel.rotation
        duration_ms = 3200
        steps = 64
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
                        if row:
                            row.set_result(tribe, colors, count)
                            self.stage_name.config(text=f"{row.name} \u2192 {tribe}")
                            pip_str = " ".join(colors)
                            self.stage_result.config(text=f"{pip_str} \u2014 {count} legal commanders found")
                        self._finish_roll()

                    self._land_wheel_on(tribe, on_landed)

                elif kind == "timeout":
                    self._stop_indefinite_spin()
                    row = self._get_row(player_id)
                    if row:
                        row.set_timeout()
                        self.stage_name.config(text=f"No valid tribe found for {row.name}")
                        self.stage_result.config(text="Try rolling again \u2014 the wheel ran out of time.")
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