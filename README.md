Anladım. Adı "Yol Telaşı" değil, "Race Game" olacak. README'yi buna göre güncelliyorum.

# Race Game

**Race Game** is a Turkish-language arcade car-dodging game written in Python using only the standard library (`tkinter`). The player steers a car along a three-lane road, avoids oncoming traffic, and collects fuel cans to increase the score. The game gets progressively faster, and the best score is saved between sessions.

> **Note:** All on-screen text and menus are in Turkish. This README is written in English.

## What the Game Does

1. **Menu:** Shows the title, controls, and the saved high score. The game waits for Space to start.
2. **Gameplay:** The player's green car stays at a fixed vertical position while the road scrolls downward, creating the illusion of movement. Enemy cars and fuel cans fall from the top.
3. **Scoring:** The score increases by 1 every frame survived. Collecting a fuel can adds 25 points.
4. **Difficulty:** Every 200 points raises the speed level (HIZ). Higher levels make enemies faster and spawn them more often.
5. **Game over:** Hitting an enemy car ends the game. If the score beats the record, it is saved to `road_rush_highscore.txt`.

## How It Works

The entire game lives in one class, `RoadRush`, with a few helper functions.

- **Main loop:** `root.after(16, ...)` calls `loop()` about 60 times per second. Game logic runs only while the state is `"playing"`.
- **Game states:** The `state` variable is `menu`, `playing`, `paused`, or `game_over`. Space switches between menu, playing, and paused. R restarts after game over.
- **Input:** Key presses are tracked in a `keys_down` set, so movement stays smooth when multiple keys are held.
- **Graphics:** Everything is drawn with Canvas primitives (rectangles, ovals, and text). No image files are used. Each car is a group of canvas items tagged `entity` and moved together.
- **Scrolling road:** Lane dashes move down each frame and wrap back to the top, creating an endless road.
- **Obstacles:** `spawn_obstacle()` creates an enemy car (84%) or a fuel can (16%) at a random x-position, avoiding placement too close to the previous one.
- **Collision detection:** AABB (axis-aligned bounding box) checks. Touching a car ends the game. Touching a fuel can removes it and awards points.
- **High score:** `load_high_score()` and `save_high_score()` read and write a text file next to the script. Errors are ignored, so a missing file never crashes the game.

## Requirements

- Python 3.x. On Windows, download it from [python.org](https://www.python.org/downloads/) and keep the **"tcl/tk and IDLE"** option checked during installation.
- No additional packages. The game uses only `os`, `random`, and `tkinter`.

## How to Run

```bash
python "Yarış oyunu_1.py"
```

Use the actual file name if you rename it.

## Controls

| Key | Action |
|-----|--------|
| Left Arrow / `A` | Move left |
| Right Arrow / `D` | Move right |
| `Space` | Start / pause / resume |
| `R` | Restart after game over |
| `Esc` | Quit |

## Configuration

Gameplay values are constants at the top of the file:

| Constant | Default | Purpose |
|----------|---------|---------|
| `MOVE_SPEED` | 7.5 | Horizontal speed of the player |
| `BASE_ENEMY_SPEED` | 4.2 | Starting speed of enemies |
| `BASE_SPAWN_FRAMES` | 55 | Frames between spawns at the start |
| `ENEMY_COLORS` | 6 colors | Colors used for enemy cars |
| `FRAME_MS` | 16 | Milliseconds per frame (about 60 FPS) |

Enemy speed is capped at 12, and the spawn interval has a minimum of 18 frames.

## Known Limitations

- **Pause overlay on some systems:** `stipple="gray50"` is ignored on Windows, so the overlay appears as a solid black panel.
- **Held keys after focus loss:** If the window loses focus while a key is held, the car may keep moving until the key is pressed and released again.
- **Unused code:** `lane_offset`, `enemy_colors_cycle`, `frames_alive`, `CURB_DARK`, and `GRASS_DARK` are defined but never used. The docstring mentions `road_rush_gui.py` and `time`, which do not match the actual file or imports.

## High Score

The best score is saved to `road_rush_highscore.txt` next to the game file. Delete this file to reset the record.

## Project Structure

```
.
├── Yarış oyunu_1.py          # Main game file
└── road_rush_highscore.txt   # Created automatically after the first game over
```

## License

This project is provided for personal and educational use.
