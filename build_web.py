"""
Build the browser version's generated assets into web/ (run with the project venv:
.venv/bin/python build_web.py):

    web/words.json     dictionary by length, extracted from game.py
    web/audio/*.mp3    one pre-synthesized speech clip per word (Piper, at build time)
    web/audio/welcome.mp3
    web/sfx/*.wav      laser / fail / music loop, copied from sounds/

Piper is only used here, offline; the shipped site contains just the audio.
Requires ffmpeg on PATH. Existing clips are skipped, so reruns only add new words.
"""
import ast
import json
import os
import shutil
import subprocess
import tempfile
import wave

from piper import PiperVoice

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
VOICE = os.path.join(ROOT, "voices", "en_US-amy-medium.onnx")
WELCOME = "Welcome to Kinnder Type. Please select your difficulty mode by pressing one or two to start the game."


def load_dictionary():
    tree = ast.parse(open(os.path.join(ROOT, "game.py"), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "DICTIONARY_BY_LENGTH":
            return ast.literal_eval(node.value)
    raise SystemExit("DICTIONARY_BY_LENGTH not found in game.py")


def to_mp3(src, dst, bitrate="40k"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-ac", "1",
                    "-codec:a", "libmp3lame", "-b:a", bitrate, dst], check=True)


def main():
    os.makedirs(os.path.join(WEB, "audio"), exist_ok=True)
    os.makedirs(os.path.join(WEB, "sfx"), exist_ok=True)

    dictionary = load_dictionary()
    with open(os.path.join(WEB, "words.json"), "w") as f:
        json.dump({str(k): v for k, v in dictionary.items()}, f)

    # Kept as WAV: MP3 encoder padding would put an audible gap in the music loop.
    for name in ("laser", "fail", "music_loop"):
        shutil.copyfile(os.path.join(ROOT, "sounds", name + ".wav"), os.path.join(WEB, "sfx", name + ".wav"))

    voice = PiperVoice.load(VOICE)
    # Normal mode also speaks single letters and punctuation marks (spoken by name).
    punct = {"p_period": "period", "p_comma": "comma", "p_apostrophe": "apostrophe", "p_dash": "dash"}
    items = [("welcome", WELCOME)]
    items += [(c, c) for c in "abcdefghijklmnopqrstuvwxyz"]
    items += list(punct.items())
    items += [(w, w) for ws in dictionary.values() for w in ws]
    with tempfile.TemporaryDirectory() as tmp:
        for name, text in items:
            out = os.path.join(WEB, "audio", name + ".mp3")
            if os.path.exists(out):
                continue
            wav_path = os.path.join(tmp, "t.wav")
            with wave.open(wav_path, "wb") as wf:
                voice.synthesize_wav(text, wf)
            to_mp3(wav_path, out)
            print("made", name)


if __name__ == "__main__":
    main()
