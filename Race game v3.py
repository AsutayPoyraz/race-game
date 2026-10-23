#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROAD RUSH (GELISMIS SURUM) - Grafiksel araba kacirma oyunu (Windows icin)

Sadece Python'un standart kutuphanesini kullanir: tkinter, random, os, time,
math, json, threading ve (Windows'a ozel) winsound. tkinter, python.org'dan
indirilen resmi Windows kurulumunda varsayilan olarak gelir, bu yuzden
hicbir "pip install" adimina gerek yoktur.

YENI OZELLIKLER:
    - Guclendiriciler: Miknatis (M), Kalkan (K), Yavas Cekim (Y)
    - Garaj: Toplanan altinlarla kalici olarak yeni araclar satin alinabilir
    - Serit degistiren (sinyal veren) yapay zeka araclari ve kaygan yag/su
      lekeleri
    - Skora bagli Gunduz/Gece dongusu ve mevsime gore hafif parcacik
      efektleri (yaprak, kar tanesi, cicek yapragi)
    - Tek seferlik gorevler / basarimlar (ekstra altin + puan odulu)
    - winsound ile arka planda (asenkron) calan kisa ses efektleri

Calistirmak icin:
    python Road_Rush_gelistirilmis.py

Kontroller:
    Sol Ok / A        -> sola git
    Sag Ok / D         -> saga git
    Bosluk             -> baslat / duraklat-devam et
    G                  -> Garaj'i ac (menu veya oyun bitti ekraninda)
    Yukari / Asagi     -> Garaj'da gezin
    Enter / Bosluk     -> Garaj'da arac sec / satin al
    Backspace          -> Garaj'dan menuye don
    R                  -> (oyun bittiginde) yeniden basla
    Esc                -> cikis
"""

import os
import json
import math
import random
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:
    winsound = None
    _HAS_WINSOUND = False

# --------------------------------------------------------------------------
# Ayarlar
# --------------------------------------------------------------------------
WIDTH = 480
HEIGHT = 700
ROAD_WIDTH = 300
ROAD_LEFT = (WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH

CAR_W, CAR_H = 46, 78
PLAYER_Y = HEIGHT - 130
MOVE_SPEED = 7.5          # varsayilan (ilk) aracin yatay hizi (piksel / frame)
FRAME_MS = 16              # ~60 FPS

BASE_ENEMY_SPEED = 4.2
BASE_SPAWN_FRAMES = 55

GRASS = "#2f6b3a"
GRASS_DARK = "#285d32"
ROAD_COLOR = "#3a3a3f"
LINE_COLOR = "#e8e8e8"
CURB_LIGHT = "#d9d9d9"
CURB_DARK = "#b23b3b"

ENEMY_COLORS = ["#c0392b", "#2980b9", "#8e44ad", "#d68910", "#16a085", "#7f8c8d"]

# Tema paletleri: arka plan/çim, bordür, gökyüzü hissi için HUD ve parçacık rengi
THEMES = [
    {"name": "ILKBAHAR", "grass": "#2f8a45", "grass_dark": "#246d36",
     "curb": "#f4f0dc", "accent": "#ff8fc7", "sky": "#aee3f5"},
    {"name": "YAZ", "grass": "#9aab35", "grass_dark": "#788629",
     "curb": "#fff2a8", "accent": "#ffd447", "sky": "#65cfff"},
    {"name": "SONBAHAR", "grass": "#a85d2a", "grass_dark": "#7d3f25",
     "curb": "#d5a06a", "accent": "#f08a32", "sky": "#9aa6b2"},
    {"name": "KIS", "grass": "#dce8ef", "grass_dark": "#b9cbd5",
     "curb": "#f7fbff", "accent": "#d9f2ff", "sky": "#c5d0da"},
]

# Mevsim indeksine gore hava parcaciği turu (None = parcacik yok)
WEATHER_STYLES = {0: "petal", 1: None, 2: "leaf", 3: "snow"}

# Garajda satin alinabilecek araclar: renk, fiyat (altin) ve yatay hiz (MOVE_SPEED)
CAR_CATALOG = [
    {"name": "Yesil Istiridye", "color": "#27ae60", "cost": 0, "move_speed": 7.5},
    {"name": "Turkuaz Sahin", "color": "#1abc9c", "cost": 150, "move_speed": 8.3},
    {"name": "Mor Hayalet", "color": "#9b59b6", "cost": 350, "move_speed": 9.1},
    {"name": "Altin Titan", "color": "#f1c40f", "cost": 700, "move_speed": 10.0},
    {"name": "Kirmizi Seytan", "color": "#e74c3c", "cost": 1100, "move_speed": 11.0},
]

# Gorev/basarim havuzu: her oyunda bu havuzdan rastgele 2 tanesi aktif olur
MISSION_POOL = [
    {"id": "near_miss_5", "desc": "Bu turda 5 kez yakin gecis yap",
     "target": 5, "type": "near_miss", "reward_coins": 30, "reward_score": 50},
    {"id": "score_1000", "desc": "Yakitin bitmeden 1000 puana ulas",
     "target": 1000, "type": "score", "reward_coins": 50, "reward_score": 100},
    {"id": "gold_5", "desc": "Bu turda 5 altin topla",
     "target": 5, "type": "gold", "reward_coins": 40, "reward_score": 60},
    {"id": "night_300", "desc": "Gece modunda 300 puan hayatta kal",
     "target": 300, "type": "night_survive", "reward_coins": 35, "reward_score": 50},
]

HIGH_SCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "road_rush_highscore.txt"
)
PROFILE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "road_rush_profile.json"
)


def load_high_score():
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_high_score(value):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(value))
    except Exception:
        pass


def load_profile():
    """Kalici altin bakiyesini, sahip olunan araclari ve secili araci yukler."""
    profile = {"coins": 0, "owned": [0], "selected": 0}
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            profile.update(data)
    except Exception:
        pass
    if not isinstance(profile.get("owned"), list):
        profile["owned"] = [0]
    if 0 not in profile["owned"]:
        profile["owned"].append(0)
    if not (0 <= profile.get("selected", 0) < len(CAR_CATALOG)):
        profile["selected"] = 0
    return profile


def save_profile(profile):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profile, f)
    except Exception:
        pass


class SoundManager:
    """Windows'un yerlesik winsound modulunu kullanarak, disaridan hicbir ses
    dosyasi veya ek kutuphane gerektirmeden kisa efektler calar. Her ses,
    ana oyun dongusunu bloklamamak icin ayri bir arka plan thread'inde
    (daemon) calinir; bu sekilde "asenkron" davranis elde edilir."""

    def __init__(self, enabled=True):
        self.enabled = enabled and _HAS_WINSOUND

    def _beep_async(self, frequency, duration_ms):
        if not self.enabled:
            return

        def _play():
            try:
                winsound.Beep(frequency, duration_ms)
            except Exception:
                pass

        threading.Thread(target=_play, daemon=True).start()

    def engine(self):
        self._beep_async(220, 60)

    def brake(self):
        self._beep_async(140, 90)

    def pickup(self):
        self._beep_async(880, 70)

    def gold(self):
        self._beep_async(1046, 70)

    def powerup(self):
        self._beep_async(660, 110)

    def shield_break(self):
        self._beep_async(300, 180)

    def crash(self):
        self._beep_async(100, 320)

    def achievement(self):
        self._beep_async(1318, 160)


class Mission(object):
    """Bir turda takip edilen tek bir gorev/basarim."""

    def __init__(self, template):
        self.id = template["id"]
        self.desc = template["desc"]
        self.target = template["target"]
        self.type = template["type"]
        self.reward_coins = template["reward_coins"]
        self.reward_score = template["reward_score"]
        self.progress = 0
        self.completed = False

    def progress_text(self):
        shown = min(self.progress, self.target)
        return "{0} ({1}/{2})".format(self.desc, shown, self.target)


class MissionManager(object):
    """Her oyun turunda aktif olan gorevleri yonetir."""

    def __init__(self):
        self.active = []
        self.start_new_run()

    def start_new_run(self):
        k = min(2, len(MISSION_POOL))
        templates = random.sample(MISSION_POOL, k=k)
        self.active = [Mission(t) for t in templates]

    def register_near_miss(self):
        for m in self.active:
            if m.type == "near_miss" and not m.completed:
                m.progress += 1

    def register_gold(self):
        for m in self.active:
            if m.type == "gold" and not m.completed:
                m.progress += 1

    def update_score(self, score):
        for m in self.active:
            if m.type == "score" and not m.completed:
                m.progress = score

    def update_night_survive(self, night_active, score_delta):
        for m in self.active:
            if m.type == "night_survive" and not m.completed:
                if night_active:
                    m.progress += score_delta
                else:
                    m.progress = 0

    def check_completions(self):
        completed_now = []
        for m in self.active:
            if not m.completed and m.progress >= m.target:
                m.completed = True
                completed_now.append(m)
        return completed_now


class RoadRush:
    def __init__(self, root):
        self.root = root
        root.title("Road Rush")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                 bg=GRASS, highlightthickness=0)
        self.canvas.pack()

        self.title_font = tkfont.Font(family="Segoe UI", size=28, weight="bold")
        self.ui_font = tkfont.Font(family="Segoe UI", size=14, weight="bold")
        self.small_font = tkfont.Font(family="Segoe UI", size=11)

        self.high_score = load_high_score()
        self.profile = load_profile()
        self.sound = SoundManager()
        self.garage_cursor = self.profile.get("selected", 0)

        self.keys_down = set()

        root.bind("<KeyPress>", self.on_key_down)
        root.bind("<KeyRelease>", self.on_key_up)

        self.state = "menu"   # menu | garage | playing | paused | game_over
        self.lane_offset = 0.0
        self.enemy_colors_cycle = ENEMY_COLORS[:]

        # Gece/gunduz durumu, ilk apply_theme() cagrisindan once var olmali
        self.night_active = False
        self.night_prev = False
        self.theme_index = -1

        self.draw_static_road()
        self.reset_game(full=True)
        self.show_menu()
        self.loop()

    # ---------------------------------------------------------------- utils
    def on_key_down(self, event):
        key = event.keysym
        was_down = key in self.keys_down
        self.keys_down.add(key)

        if key == "Escape":
            self.root.destroy()
            return

        if self.state == "garage":
            if key in ("Up", "w", "W"):
                self.garage_cursor = (self.garage_cursor - 1) % len(CAR_CATALOG)
                self.show_garage()
            elif key in ("Down", "s", "S"):
                self.garage_cursor = (self.garage_cursor + 1) % len(CAR_CATALOG)
                self.show_garage()
            elif key in ("Return", "space"):
                self.garage_select_or_buy()
            elif key == "BackSpace":
                self.state = "menu"
                self.show_menu()
            return

        if key == "space":
            if self.state == "menu":
                self.start_game()
            elif self.state == "playing":
                self.state = "paused"
                self.show_pause_overlay()
            elif self.state == "paused":
                self.state = "playing"
                self.clear_overlay()

        if key.lower() == "g" and self.state in ("menu", "game_over"):
            self.state = "garage"
            self.garage_cursor = self.profile.get("selected", 0)
            self.show_garage()
            return

        if key.lower() == "r" and self.state == "game_over":
            self.start_game()

        if self.state == "playing" and not was_down and key in (
                "Left", "Right", "a", "A", "d", "D"):
            self.sound.engine()

    def on_key_up(self, event):
        self.keys_down.discard(event.keysym)

    # ---------------------------------------------------------- road / HUD
    def draw_static_road(self):
        # cim (kenarlar) zaten canvas arka plani; asfalt ve bordurler sabit
        self.canvas.create_rectangle(ROAD_LEFT - 10, 0, ROAD_LEFT, HEIGHT,
                                      fill=CURB_LIGHT, outline="")
        self.canvas.create_rectangle(ROAD_RIGHT, 0, ROAD_RIGHT + 10, HEIGHT,
                                      fill=CURB_LIGHT, outline="")
        self.canvas.create_rectangle(ROAD_LEFT, 0, ROAD_RIGHT, HEIGHT,
                                      fill=ROAD_COLOR, outline="")

        lane_w = ROAD_WIDTH / 3
        self.divider_xs = [ROAD_LEFT + lane_w, ROAD_LEFT + 2 * lane_w]

        self.lane_lines = []
        dash_len, gap = 28, 22
        period = dash_len + gap
        for x in self.divider_xs:
            y = -period
            while y < HEIGHT + period:
                lid = self.canvas.create_rectangle(
                    x - 2, y, x + 2, y + dash_len, fill=LINE_COLOR, outline="")
                self.lane_lines.append(lid)
                y += period

        self.scenery_ids = []
        self.make_scenery()

        self.hud_score = self.canvas.create_text(
            14, 14, anchor="nw", fill="white", font=self.ui_font, text="SKOR: 0")
        self.hud_best = self.canvas.create_text(
            WIDTH - 14, 14, anchor="ne", fill="white", font=self.ui_font,
            text=f"REKOR: {self.high_score}")
        self.hud_speed = self.canvas.create_text(
            14, 40, anchor="nw", fill="#f1c40f", font=self.small_font, text="HIZ: 1")
        self.hud_powerups = self.canvas.create_text(
            14, 64, anchor="nw", fill="#00e5ff", font=self.small_font, text="")
        self.hud_missions = self.canvas.create_text(
            14, 86, anchor="nw", fill="#f1c40f", font=self.small_font, text="",
            width=260)
        self.hud_fuel_label = self.canvas.create_text(
            WIDTH - 14, 42, anchor="ne", fill="white", font=self.small_font, text="YAKIT: %100")
        self.fuel_bar_bg = self.canvas.create_rectangle(
            WIDTH - 154, 60, WIDTH - 14, 76, fill="#263238", outline="white")
        self.fuel_bar = self.canvas.create_rectangle(
            WIDTH - 152, 62, WIDTH - 16, 74, fill="#2ecc71", outline="")
        self.hud_theme = self.canvas.create_text(
            WIDTH / 2, 14, anchor="n", fill="white", font=self.small_font, text="ILKBAHAR")

        self.overlay_items = []
        self.banner_items = []
        self.apply_theme(0, immediate=True)

    def make_scenery(self):
        """Yol kenarına basit mevsimsel ağaç/çiçek ayrıntıları ekler."""
        for item in self.scenery_ids:
            self.canvas.delete(item)
        self.scenery_ids = []
        for side in ("left", "right"):
            x_base = ROAD_LEFT - 30 if side == "left" else ROAD_RIGHT + 30
            for y in range(70, HEIGHT, 145):
                trunk = self.canvas.create_rectangle(x_base - 3, y + 8, x_base + 3, y + 24,
                                                     fill="#795548", outline="")
                crown = self.canvas.create_oval(x_base - 16, y - 12, x_base + 16, y + 18,
                                                 fill="#237a3b", outline="")
                flower = self.canvas.create_oval(x_base + (9 if side == "left" else -13),
                                                  y + 28, x_base + (15 if side == "left" else -7),
                                                  y + 34, fill="#ff8fc7", outline="")
                self.scenery_ids.extend([trunk, crown, flower])

    def apply_theme(self, score, immediate=False):
        """Skora ve gece/gunduz durumuna gore tema secer; 2800 puanda mevsim
        donguyu basa sarar, 400 puanda bir gece/gunduz gecisi tetiklenir."""
        theme_index = int((score % 2800) // 700)
        theme = THEMES[theme_index]
        night_changed = self.night_active != getattr(self, "night_prev", None)

        if theme_index != getattr(self, "theme_index", -1) or night_changed or immediate:
            try:
                current_bg = self.canvas.cget("bg")
            except tk.TclError:
                current_bg = theme["grass"]
            self.theme_from_color = current_bg
            self.theme_index = theme_index
            self.theme_target = theme
            self.night_prev = self.night_active
            self.transition_step = 0
            label = theme["name"] + ("  (GECE)" if self.night_active else "")
            self.canvas.itemconfig(self.hud_theme, text=label)

        if not hasattr(self, "theme_target"):
            self.theme_target = theme
            self.theme_from_color = theme["grass"]
            self.transition_step = 10

        target_grass = self.theme_target["grass"]
        if self.night_active:
            target_grass = self._blend_color(target_grass, "#000000", 0.55)

        if self.transition_step < 10:
            self.transition_step += 1
            t = self.transition_step / 10.0
            self.canvas.configure(bg=self._blend_color(
                self.theme_from_color, target_grass, t))
        else:
            self.canvas.configure(bg=target_grass)

        self.canvas.itemconfig(self.fuel_bar_bg, outline=self.theme_target["curb"])
        for index, item in enumerate(self.scenery_ids):
            if index % 3 == 1:
                color = ["#2f8a45", "#1d7835", "#c85b27", "#f2f6f8"][theme_index]
                self.canvas.itemconfig(item, fill=color)
            elif index % 3 == 2:
                color = ["#ff8fc7", "#ffd447", "#d94d2b", "#ffffff"][theme_index]
                self.canvas.itemconfig(item, fill=color)

    @staticmethod
    def _blend_color(start, end, amount):
        try:
            a = tuple(int(start[i:i+2], 16) for i in (1, 3, 5))
            b = tuple(int(end[i:i+2], 16) for i in (1, 3, 5))
            return "#%02x%02x%02x" % tuple(round(x + (y-x)*amount) for x, y in zip(a, b))
        except Exception:
            return end

    def scroll_lanes(self, dy):
        period = 50
        for lid in self.lane_lines:
            self.canvas.move(lid, 0, dy)
            coords = self.canvas.coords(lid)
            if coords and coords[1] > HEIGHT:
                self.canvas.move(lid, 0, -(period * ((HEIGHT + period) // period + 1)))

    # ------------------------------------------------------------ hava durumu
    def spawn_weather_particle(self):
        style = WEATHER_STYLES.get(getattr(self, "theme_index", 0))
        if style is None:
            return
        x = random.uniform(10, WIDTH - 10)
        y = -10
        speed = random.uniform(1.5, 3.2)
        drift = random.uniform(-0.6, 0.6)
        if style == "snow":
            pid = self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3,
                                          fill="#ffffff", outline="")
        elif style == "petal":
            pid = self.canvas.create_oval(x - 4, y - 2, x + 4, y + 2,
                                          fill="#ffb6d9", outline="")
        else:  # leaf
            pid = self.canvas.create_oval(x - 4, y - 3, x + 4, y + 3,
                                          fill="#d9772e", outline="")
        self.weather_particles.append({"id": pid, "x": x, "y": y,
                                       "speed": speed, "drift": drift})

    def update_weather(self):
        style = WEATHER_STYLES.get(getattr(self, "theme_index", 0))
        if style is not None and len(self.weather_particles) < 22 and random.random() < 0.6:
            self.spawn_weather_particle()
        for p in list(self.weather_particles):
            self.canvas.move(p["id"], p["drift"], p["speed"])
            p["x"] += p["drift"]
            p["y"] += p["speed"]
            if p["y"] > HEIGHT + 10 or style is None:
                self.canvas.delete(p["id"])
                self.weather_particles.remove(p)

    # --------------------------------------------------------------- araba
    def make_car(self, x, y, color, facing_up=True):
        """Basit, sevimli bir araba sekli olusturur; canvas item id listesi
        dondurur (hepsi birlikte hareket ettirilecek). Son iki id her zaman
        farlardir (gece modunda parlaklik degistirmek icin kullanilir)."""
        ids = []
        ids.append(self.canvas.create_rectangle(
            x, y, x + CAR_W, y + CAR_H, fill=color, outline="#1b1b1b", width=2))
        glass_y = (y + 10) if facing_up else (y + CAR_H - 26)
        ids.append(self.canvas.create_rectangle(
            x + 7, glass_y, x + CAR_W - 7, glass_y + 16,
            fill="#aee3f5", outline="#1b1b1b"))
        # tekerlekler
        ids.append(self.canvas.create_rectangle(
            x - 3, y + 10, x + 3, y + 24, fill="#111111", outline=""))
        ids.append(self.canvas.create_rectangle(
            x + CAR_W - 3, y + 10, x + CAR_W + 3, y + 24, fill="#111111", outline=""))
        ids.append(self.canvas.create_rectangle(
            x - 3, y + CAR_H - 24, x + 3, y + CAR_H - 10, fill="#111111", outline=""))
        ids.append(self.canvas.create_rectangle(
            x + CAR_W - 3, y + CAR_H - 24, x + CAR_W + 3, y + CAR_H - 10,
            fill="#111111", outline=""))
        # farlar (son iki id)
        light_y = (y + CAR_H - 10) if facing_up else (y + 2)
        ids.append(self.canvas.create_oval(
            x + 6, light_y, x + 14, light_y + 7, fill="#fff3b0", outline=""))
        ids.append(self.canvas.create_oval(
            x + CAR_W - 14, light_y, x + CAR_W - 6, light_y + 7,
            fill="#fff3b0", outline=""))
        return ids

    def set_car_lights(self, ids, night):
        """Gece modunda bir aracin farlarini (ids listesinin son iki ogesi)
        daha parlak bir renge cevirir; bu, tam bir karanlik/aydinlatma
        simulasyonu yerine basitlestirilmis gorsel bir yaklasimdir."""
        if len(ids) < 2:
            return
        color = "#fffde7" if night else "#fff3b0"
        for lid in ids[-2:]:
            try:
                self.canvas.itemconfig(lid, fill=color)
            except tk.TclError:
                pass

    def make_fuel_can(self, x, y):
        ids = []
        w, h = 30, 36
        ids.append(self.canvas.create_rectangle(
            x, y, x + w, y + h, fill="#f1c40f", outline="#8a6d00", width=2))
        ids.append(self.canvas.create_rectangle(
            x + w * 0.3, y - 8, x + w * 0.7, y, fill="#8a6d00", outline=""))
        ids.append(self.canvas.create_text(
            x + w / 2, y + h / 2, text="F", fill="#8a6d00",
            font=self.small_font))
        return ids

    def make_powerup_icon(self, kind, x, y):
        """Miknatis (M), Kalkan (K) ve Yavas Cekim (Y) guclendirici simgeleri."""
        w = h = 34
        cx, cy = x + w / 2, y + h / 2
        if kind == "magnet":
            body = self.canvas.create_oval(x, y, x + w, y + h,
                                           fill="#8e44ad", outline="#3d1850", width=2)
            label = "M"
        elif kind == "shield":
            body = self.canvas.create_oval(x, y, x + w, y + h,
                                           fill="#16a085", outline="#0b4f41", width=2)
            label = "K"
        else:  # slowmo
            body = self.canvas.create_oval(x, y, x + w, y + h,
                                           fill="#2980b9", outline="#123a52", width=2)
            label = "Y"
        text = self.canvas.create_text(cx, cy, text=label, fill="white",
                                       font=("Segoe UI", 15, "bold"))
        return [body, text]

    def make_oil_slick(self, x, y):
        w, h = 70, 24
        ids = [self.canvas.create_oval(
            x, y, x + w, y + h, fill="#1b1b1b", outline="#000000",
            width=2, stipple="gray50")]
        return ids

    def create_shield_halo(self):
        pad = 10
        halo = self.canvas.create_oval(
            self.player_x - pad, PLAYER_Y - pad,
            self.player_x + CAR_W + pad, PLAYER_Y + CAR_H + pad,
            outline="#00e5ff", width=3, fill="", stipple="gray25")
        self.canvas.addtag_withtag("entity", halo)
        self.canvas.tag_raise(halo)
        return halo

    # -------------------------------------------------------------- durum
    def reset_game(self, full=False):
        for item in self.canvas.find_withtag("entity"):
            self.canvas.delete(item)
        for p in getattr(self, "weather_particles", []):
            self.canvas.delete(p["id"])
        self.weather_particles = []
        for i in getattr(self, "banner_items", []):
            try:
                self.canvas.delete(i)
            except tk.TclError:
                pass
        self.banner_items = []

        car_index = self.profile.get("selected", 0)
        if car_index not in self.profile.get("owned", [0]):
            car_index = 0
        car = CAR_CATALOG[car_index]
        self.move_speed = car["move_speed"]

        self.player_x = ROAD_LEFT + ROAD_WIDTH / 2 - CAR_W / 2
        self.player_ids = self.make_car(self.player_x, PLAYER_Y, car["color"],
                                         facing_up=True)
        for i in self.player_ids:
            self.canvas.addtag_withtag("entity", i)
            self.canvas.tag_raise(i)

        self.obstacles = []       # her biri: {ids, x, y, w, h, kind, ...}
        self.score = 0
        self.fuel = 100.0
        self.fuel_time_accumulator = 0.0
        self.last_update_time = time.monotonic()
        self.score_pulse = 0
        self.frames_alive = 0
        self.spawn_timer = BASE_SPAWN_FRAMES
        self.last_spawn_x = None

        # Guclendirici / gorev / gece-gunduz durumu
        self.run_coins = 0
        self.magnet_timer = 0
        self.slowmo_timer = 0
        self.slip_timer = 0
        self.invincible_timer = 0
        self.shield_active = False
        self.shield_halo_id = None
        self.night_active = False
        self.night_prev = False
        self.missions = MissionManager()

        if not full:
            self.canvas.itemconfig(self.hud_score, text="SKOR: 0")
            self.canvas.itemconfig(self.hud_speed, text="HIZ: 1")
            self.canvas.itemconfig(self.hud_powerups, text="")
            self.canvas.itemconfig(self.hud_missions, text="")
            self.update_fuel_hud()
            self.apply_theme(0, immediate=True)

    def start_game(self):
        self.clear_overlay()
        self.reset_game()
        self.state = "playing"
        self.sound.engine()

    def update_fuel_hud(self):
        fuel = max(0.0, min(100.0, self.fuel))
        self.canvas.coords(self.fuel_bar, WIDTH - 152, 62,
                           WIDTH - 152 + 136 * fuel / 100.0, 74)
        self.canvas.itemconfig(self.hud_fuel_label, text=f"YAKIT: %{int(fuel)}")
        color = "#e74c3c" if fuel < 20 else ("#f1c40f" if fuel < 45 else "#2ecc71")
        if fuel < 20 and (self.frames_alive // 12) % 2 == 0:
            color = "#ff1744"
        self.canvas.itemconfig(self.fuel_bar, fill=color)

    def add_bonus_score(self, points, x=None, y=None, message=None):
        self.score += points
        self.score_pulse = 10
        if message and x is not None and y is not None:
            flash = self.canvas.create_text(x, y, text=message, fill="#ffe66d",
                                            font=("Segoe UI", 16, "bold"))
            self.canvas.after(450, lambda item=flash: self.canvas.delete(item))

    # ------------------------------------------------------------- overlay
    def clear_overlay(self):
        for item in self.overlay_items:
            self.canvas.delete(item)
        self.overlay_items = []

    def overlay_panel(self, lines):
        self.clear_overlay()
        panel = self.canvas.create_rectangle(
            40, HEIGHT / 2 - 120, WIDTH - 40, HEIGHT / 2 + 120,
            fill="#000000", outline="#ffffff", width=2, stipple="gray50")
        self.overlay_items.append(panel)
        n = max(1, len(lines))
        step = min(36, 200 / n)
        y = HEIGHT / 2 - 100
        for text, fnt, color in lines:
            item = self.canvas.create_text(
                WIDTH / 2, y, text=text, fill=color, font=fnt, justify="center",
                width=WIDTH - 100)
            self.overlay_items.append(item)
            y += step

    def show_menu(self):
        self.overlay_panel([
            ("ROAD RUSH", self.title_font, "#ffffff"),
            ("Baslamak icin BOSLUK tusuna bas", self.ui_font, "#f1c40f"),
            ("Sol/Sag Ok veya A / D ile yon degistir", self.small_font, "#dddddd"),
            ("Diger arabalara carpma; yakit (F), altin ($) ve guclendirici topla",
             self.small_font, "#dddddd"),
            ("Garaj icin G'ye bas", self.small_font, "#aee3f5"),
            (f"Toplam Altin: {self.profile['coins']}", self.small_font, "#f1c40f"),
            (f"Rekor: {self.high_score}", self.small_font, "#aee3f5"),
        ])

    def show_pause_overlay(self):
        self.overlay_panel([
            ("DURAKLATILDI", self.title_font, "#ffffff"),
            ("Devam etmek icin BOSLUK", self.ui_font, "#f1c40f"),
        ])

    def show_game_over(self):
        new_best = self.score > self.high_score
        if new_best:
            self.high_score = self.score
            save_high_score(self.high_score)
        self.profile["coins"] += self.run_coins
        save_profile(self.profile)
        self.canvas.itemconfig(self.hud_best, text=f"REKOR: {self.high_score}")

        lines = [
            ("OYUN BITTI", self.title_font, "#e74c3c"),
            (f"Skor: {self.score}", self.ui_font, "#ffffff"),
            (f"Kazanilan Altin: {self.run_coins}", self.small_font, "#f1c40f"),
            (f"Toplam Altin: {self.profile['coins']}", self.small_font, "#f1c40f"),
        ]
        if new_best:
            lines.append(("YENI REKOR!", self.ui_font, "#f1c40f"))
        lines.append(("Yeniden baslamak icin R", self.small_font, "#dddddd"))
        lines.append(("Garaj icin G, cikmak icin ESC", self.small_font, "#dddddd"))
        self.overlay_panel(lines)

    def show_achievement_banner(self, mission):
        text = (f"GOREV TAMAMLANDI: {mission.desc}  "
                f"(+{mission.reward_score} puan, +{mission.reward_coins} altin)")
        bg = self.canvas.create_rectangle(
            30, 96, WIDTH - 30, 136, fill="#1b1b1b", outline="#f1c40f",
            width=2, stipple="gray25")
        label = self.canvas.create_text(
            WIDTH / 2, 116, text=text, fill="#f1c40f", font=self.small_font,
            width=WIDTH - 70, justify="center")
        self.banner_items.extend([bg, label])
        self.canvas.after(2200, lambda ids=(bg, label): self._remove_banner(ids))

    def _remove_banner(self, ids):
        for i in ids:
            try:
                self.canvas.delete(i)
            except tk.TclError:
                pass
            if i in self.banner_items:
                self.banner_items.remove(i)

    # -------------------------------------------------------------- garaj
    def garage_select_or_buy(self):
        idx = self.garage_cursor
        car = CAR_CATALOG[idx]
        if idx in self.profile["owned"]:
            self.profile["selected"] = idx
            save_profile(self.profile)
            self.sound.pickup()
        else:
            if self.profile["coins"] >= car["cost"]:
                self.profile["coins"] -= car["cost"]
                self.profile["owned"].append(idx)
                self.profile["selected"] = idx
                save_profile(self.profile)
                self.sound.achievement()
            else:
                self.sound.brake()
        self.show_garage()

    def show_garage(self):
        self.clear_overlay()
        panel = self.canvas.create_rectangle(
            20, 60, WIDTH - 20, HEIGHT - 60, fill="#000000", outline="#ffffff",
            width=2, stipple="gray50")
        self.overlay_items.append(panel)

        title = self.canvas.create_text(WIDTH / 2, 90, text="GARAJ",
                                        fill="#ffffff", font=self.title_font)
        self.overlay_items.append(title)
        coins_text = self.canvas.create_text(
            WIDTH / 2, 125, text=f"Altin: {self.profile['coins']}",
            fill="#f1c40f", font=self.ui_font)
        self.overlay_items.append(coins_text)

        y = 165
        for idx, car in enumerate(CAR_CATALOG):
            owned = idx in self.profile["owned"]
            selected = idx == self.profile["selected"]
            cursor = idx == self.garage_cursor
            if selected:
                status = "SECILI"
            elif owned:
                status = "SAHIP"
            else:
                status = f"{car['cost']} Altin"
            prefix = "> " if cursor else "   "
            if selected:
                color = "#2ecc71"
            elif owned:
                color = "#aee3f5"
            elif self.profile["coins"] >= car["cost"]:
                color = "#f1c40f"
            else:
                color = "#e74c3c"

            swatch = self.canvas.create_rectangle(
                70, y - 10, 94, y + 10, fill=car["color"], outline="#ffffff")
            label = self.canvas.create_text(
                110, y, anchor="w",
                text=f"{prefix}{car['name']}  -  Hiz:{car['move_speed']:.1f}  -  {status}",
                fill=color, font=self.small_font)
            self.overlay_items.extend([swatch, label])
            y += 34

        hint = self.canvas.create_text(
            WIDTH / 2, HEIGHT - 85,
            text="Yukari/Asagi: gez   Enter: sec/satin al   Backspace: geri",
            fill="#dddddd", font=self.small_font, justify="center", width=WIDTH - 80)
        self.overlay_items.append(hint)

    # --------------------------------------------------------------- loop
    def loop(self):
        if self.state == "playing":
            self.update_playing()
        self.root.after(FRAME_MS, self.loop)

    def update_playing(self):
        now = time.monotonic()
        elapsed = min(0.1, max(0.0, now - getattr(self, "last_update_time", now)))
        self.last_update_time = now
        self.fuel = max(0.0, self.fuel - 2.0 * elapsed)
        self.update_fuel_hud()
        if self.fuel <= 0:
            self.sound.crash()
            self.state = "game_over"
            self.show_game_over()
            return

        self.frames_alive += 1
        self.night_active = ((self.score // 400) % 2 == 1)

        speed_level = 1 + self.score // 200
        enemy_speed = min(12.0, BASE_ENEMY_SPEED + speed_level * 0.9)
        spawn_interval = max(18, BASE_SPAWN_FRAMES - speed_level * 4)
        if self.slowmo_timer > 0:
            enemy_speed *= 0.5
            spawn_interval = int(spawn_interval * 1.6)

        # --- oyuncu hareketi ---
        dx = 0.0
        if ("Left" in self.keys_down) or ("a" in self.keys_down) or ("A" in self.keys_down):
            dx -= self.move_speed
        if ("Right" in self.keys_down) or ("d" in self.keys_down) or ("D" in self.keys_down):
            dx += self.move_speed
        if self.slip_timer > 0:
            # Yag/su lekesine basildiginda direksiyon hassasiyeti gecici olarak bozulur
            dx += math.sin(self.frames_alive * 0.9) * 6.0 * (self.slip_timer / 40.0)

        real_dx = 0.0
        if abs(dx) > 0.01:
            new_x = self.player_x + dx
            new_x = max(ROAD_LEFT + 4, min(ROAD_RIGHT - CAR_W - 4, new_x))
            real_dx = new_x - self.player_x
            if abs(real_dx) > 0.01:
                for i in self.player_ids:
                    self.canvas.move(i, real_dx, 0)
                self.player_x = new_x

        if self.shield_active and self.shield_halo_id is not None and abs(real_dx) > 0.01:
            self.canvas.move(self.shield_halo_id, real_dx, 0)

        self.set_car_lights(self.player_ids, self.night_active)

        # --- yol cizgilerini kaydir + hava durumu ---
        self.scroll_lanes(enemy_speed)
        self.update_weather()

        # --- dusmanlari / yakit-altin-guclendirici nesnelerini hareket ettir ---
        for ob in list(self.obstacles):
            for i in ob["ids"]:
                self.canvas.move(i, 0, enemy_speed)
            ob["y"] += enemy_speed

            if ob["y"] > HEIGHT + 20:
                for i in ob["ids"]:
                    self.canvas.delete(i)
                self.obstacles.remove(ob)
                continue

            if ob["kind"] == "car":
                self.set_car_lights(ob["ids"], self.night_active)
                if ob.get("lane_change"):
                    diff = ob["target_x"] - ob["x"]
                    if abs(diff) > 0.5:
                        step = max(-ob["drift_speed"], min(ob["drift_speed"], diff))
                        for i in ob["ids"]:
                            self.canvas.move(i, step, 0)
                        ob["x"] += step
                        phase = (self.frames_alive + ob.get("blink_phase", 0)) % 20
                        blink_color = "#ff6f00" if phase < 10 else "#fff3b0"
                        for lid in ob["ids"][-2:]:
                            self.canvas.itemconfig(lid, fill=blink_color)

            if self.magnet_timer > 0 and ob["kind"] in ("gold", "fuel"):
                target_cx = self.player_x + CAR_W / 2
                cur_cx = ob["x"] + ob["w"] / 2
                diff = target_cx - cur_cx
                if abs(diff) > 1.0:
                    step = max(-12.0, min(12.0, diff))
                    for i in ob["ids"]:
                        self.canvas.move(i, step, 0)
                    ob["x"] += step

            hit = (ob["x"] < self.player_x + CAR_W and ob["x"] + ob["w"] > self.player_x
                   and ob["y"] < PLAYER_Y + CAR_H and ob["y"] + ob["h"] > PLAYER_Y)

            if hit:
                if ob["kind"] == "car":
                    if self.invincible_timer <= 0:
                        if self.shield_active:
                            self.shield_active = False
                            if self.shield_halo_id is not None:
                                self.canvas.delete(self.shield_halo_id)
                                self.shield_halo_id = None
                            self.invincible_timer = 45
                            self.sound.shield_break()
                            self.add_bonus_score(0, ob["x"] + ob["w"] / 2, ob["y"],
                                                  "KALKAN KIRILDI!")
                            for i in ob["ids"]:
                                self.canvas.delete(i)
                            self.obstacles.remove(ob)
                            continue
                        else:
                            self.sound.crash()
                            self.state = "game_over"
                            self.show_game_over()
                            return
                elif ob["kind"] == "fuel":
                    self.fuel = min(100.0, self.fuel + 25.0)
                    self.update_fuel_hud()
                    self.sound.pickup()
                    self.add_bonus_score(0, ob["x"] + ob["w"] / 2, ob["y"], "+%25 YAKIT")
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue
                elif ob["kind"] == "gold":
                    self.add_bonus_score(20, ob["x"] + ob["w"] / 2, ob["y"], "+20")
                    self.run_coins += 10
                    self.missions.register_gold()
                    self.sound.gold()
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue
                elif ob["kind"] == "magnet":
                    self.magnet_timer = 300
                    self.sound.powerup()
                    self.add_bonus_score(5, ob["x"] + ob["w"] / 2, ob["y"], "MIKNATIS!")
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue
                elif ob["kind"] == "shield":
                    if not self.shield_active:
                        self.shield_active = True
                        self.shield_halo_id = self.create_shield_halo()
                        self.add_bonus_score(5, ob["x"] + ob["w"] / 2, ob["y"], "KALKAN!")
                    else:
                        self.add_bonus_score(15, ob["x"] + ob["w"] / 2, ob["y"], "+15")
                    self.sound.powerup()
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue
                elif ob["kind"] == "slowmo":
                    self.slowmo_timer = 240
                    self.sound.powerup()
                    self.add_bonus_score(5, ob["x"] + ob["w"] / 2, ob["y"], "YAVAS CEKIM!")
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue
                elif ob["kind"] == "oil":
                    self.slip_timer = 40
                    self.sound.brake()
                    self.add_bonus_score(0, ob["x"] + ob["w"] / 2, ob["y"], "KAYDIN!")
                    for i in ob["ids"]:
                        self.canvas.delete(i)
                    self.obstacles.remove(ob)
                    continue

            # Trafik arabası oyuncuyu geçtiyse yakın geçişi yalnızca bir kez kontrol et.
            if ob["kind"] == "car" and not ob.get("passed", False) and ob["y"] > PLAYER_Y + CAR_H:
                ob["passed"] = True
                horizontal_gap = max(ob["x"] - (self.player_x + CAR_W),
                                     self.player_x - (ob["x"] + ob["w"]), 0)
                if horizontal_gap <= 22:
                    self.add_bonus_score(20, ob["x"] + ob["w"] / 2, PLAYER_Y - 12,
                                          "YAKIN GECIS +20")
                    self.missions.register_near_miss()

        # --- yeni dusman/yakit/altin/guclendirici uret ---
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            self.spawn_timer = spawn_interval
            self.spawn_obstacle()

        # --- skor ve HUD ---
        self.score += 1
        self.canvas.itemconfig(self.hud_score, text=f"SKOR: {self.score}")
        if self.score_pulse > 0:
            self.canvas.itemconfig(self.hud_score, font=("Segoe UI", 17, "bold"))
            self.score_pulse -= 1
        else:
            self.canvas.itemconfig(self.hud_score, font=self.ui_font)
        self.canvas.itemconfig(self.hud_speed, text=f"HIZ: {speed_level}")
        self.apply_theme(self.score)
        if self.slowmo_timer > 0:
            blended = self._blend_color(self.canvas.cget("bg"), "#3b6bdb", 0.4)
            self.canvas.configure(bg=blended)

        # --- gorevleri guncelle ---
        self.missions.update_score(self.score)
        self.missions.update_night_survive(self.night_active, 1)
        for m in self.missions.check_completions():
            self.run_coins += m.reward_coins
            self.add_bonus_score(m.reward_score)
            self.sound.achievement()
            self.show_achievement_banner(m)

        labels = []
        if self.magnet_timer > 0:
            labels.append("MIKNATIS")
        if self.shield_active:
            labels.append("KALKAN")
        if self.slowmo_timer > 0:
            labels.append("YAVAS CEKIM")
        self.canvas.itemconfig(self.hud_powerups, text="  ".join(labels))

        mission_lines = [("[OK] " if m.completed else "- ") + m.progress_text()
                          for m in self.missions.active]
        self.canvas.itemconfig(self.hud_missions, text="\n".join(mission_lines))

        # --- zamanlayicilari azalt ---
        if self.magnet_timer > 0:
            self.magnet_timer -= 1
        if self.slowmo_timer > 0:
            self.slowmo_timer -= 1
        if self.slip_timer > 0:
            self.slip_timer -= 1
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

    def spawn_obstacle(self):
        margin = 6
        min_x = ROAD_LEFT + margin

        def pick_x(width):
            local_max = ROAD_RIGHT - margin - width
            x = min_x
            for _ in range(6):
                x = random.uniform(min_x, local_max)
                if self.last_spawn_x is None or abs(x - self.last_spawn_x) > CAR_W * 0.9:
                    break
            self.last_spawn_x = x
            return x

        roll = random.random()
        lane_change = False
        target_x = None

        if roll < 0.05:
            kind = "magnet"
            w = h = 34
            x = pick_x(w)
            ids = self.make_powerup_icon("magnet", x, -h)
        elif roll < 0.08:
            kind = "shield"
            w = h = 34
            x = pick_x(w)
            ids = self.make_powerup_icon("shield", x, -h)
        elif roll < 0.11:
            kind = "slowmo"
            w = h = 34
            x = pick_x(w)
            ids = self.make_powerup_icon("slowmo", x, -h)
        elif roll < 0.17:
            kind = "fuel"
            w, h = 30, 36
            x = pick_x(w)
            ids = self.make_fuel_can(x, -h)
        elif roll < 0.32:
            kind = "gold"
            w, h = 28, 28
            x = pick_x(w)
            cx, cy = x + w / 2, -h + h / 2
            ids = [
                self.canvas.create_oval(x, -h, x + w, 0, fill="#f1c40f",
                                        outline="#fff2a8", width=3),
                self.canvas.create_text(cx, cy, text="$", fill="#7d5a00",
                                        font=("Segoe UI", 15, "bold")),
            ]
        elif roll < 0.40:
            kind = "oil"
            w, h = 70, 24
            x = pick_x(w)
            ids = self.make_oil_slick(x, -h)
        else:
            kind = "car"
            w, h = CAR_W, CAR_H
            x = pick_x(w)
            color = random.choice(ENEMY_COLORS)
            ids = self.make_car(x, -h, color, facing_up=False)
            if random.random() < 0.28:
                lane_change = True
                lane_w = ROAD_WIDTH / 3
                shift = lane_w * random.choice([-1, 1])
                local_max = ROAD_RIGHT - margin - w
                target_x = min(max(x + shift, min_x), local_max)

        for i in ids:
            self.canvas.addtag_withtag("entity", i)

        ob = {"ids": ids, "x": x, "y": -h, "w": w, "h": h, "kind": kind,
              "passed": False}
        if kind == "car":
            ob["lane_change"] = lane_change
            ob["target_x"] = target_x
            ob["drift_speed"] = random.uniform(0.6, 1.4)
            ob["blink_phase"] = random.randint(0, 19)

        self.obstacles.append(ob)


def main():
    root = tk.Tk()
    RoadRush(root)
    root.mainloop()


if __name__ == "__main__":
    main()