# Kinder Type

An Asteroids-style typing game for beginners. A little ship at the bottom of
the screen fires lasers at letters and words — type the highlighted
character to shoot it.

## Modes

- **Beginner Mode** — one word at a time, shown center-screen with no time
  pressure. The onscreen keyboard  highlights the next key to press by blinking
  red. The word is spoken aloud when it appears. As your
  score climbs, longer and more advanced words are included. Every 500
  points unlocks the next word length, from 3 letters up to 13.

- **Normal Mode** — words fall from the top and speed up gradually over a
  10-minute ramp. Destroy each word before it reaches the bottom; you have
  5 lives. Completed words are read aloud.

Vocabulary is hand-curated to be kid friendly and leans STEM: colors, animals,
space, vehicles, engineering, measurement units, tools, and more — over
1,000 words in Beginner mode.

## Controls

| Key | Action |
|---|---|
| `1` / `2` | Start Beginner / Normal mode (from the menu) |
| Letter keys | Type the highlighted target |
| `M` | Mute / unmute (menu screen only) |
| `Esc` | Back to menu (quits from the menu itself) |

## Running it

**Linux / macOS**
```
./run.sh
```

**Windows**
```
run.bat
```

Either script will set up everything on first run (creates a virtual
environment, installs dependencies, downloads the text-to-speech voice
model, generates sound effects and music) via `install.py`, then launches
the game. Re-running only checks for missing steps, then
launches the game.

You can also run the installer directly: `python3 install.py` (or
`python install.py` on Windows).

### Requirements

- Python 3.9+
- Working speakers or headphones

Everything (pygame-ce, numpy, piper-tts, the voice model, generated
audio) is installed automatically by `install.py`.

## How it's built

- **[pygame-ce](https://pyga.me)** for the game loop and rendering.
- **[Piper](https://github.com/OHF-voice/piper1-gpl)** for offline
  text-to-speech, run as a long-lived subprocess (not imported as a
  library — see `NOTICE` for why that distinction matters for licensing).
- Sound effects and the background music track are synthesized from
  scratch with `numpy` (see `generate_audio.py`) — no external audio
  assets.

## License

Apache License 2.0 — see `LICENSE`. Third-party dependency licenses are
listed in `NOTICE`.
