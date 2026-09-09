"""
One-time build script that synthesizes the game's audio (no external audio
assets — everything is generated from scratch with numpy) and writes it to
the sounds/ directory:

    sounds/laser.wav       short descending zap for each keystroke shot
    sounds/music_loop.wav  seamless looping trance backing track

Run with: .venv/bin/python generate_audio.py
"""

import os
import wave

import numpy as np

SR = 44100
OUT_DIR = os.path.join(os.path.dirname(__file__), "sounds")


def to_pcm16(audio):
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767).astype(np.int16)


def write_wav(path, audio, channels=1):
    pcm = to_pcm16(audio)
    with wave.open(path, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def fade_edges(audio, fade_samples=64):
    n = len(audio)
    fade_samples = min(fade_samples, n // 2)
    ramp = np.linspace(0.0, 1.0, fade_samples)
    if audio.ndim == 2:
        ramp = ramp[:, None]
    audio[:fade_samples] *= ramp
    audio[-fade_samples:] *= ramp[::-1]
    return audio


def to_stereo(mono_or_stereo):
    arr = np.asarray(mono_or_stereo)
    if arr.ndim == 1:
        return np.stack([arr, arr], axis=-1)
    return arr


def pan(mono, p):
    """Constant-power pan: p in [-1 (left), 1 (right)]."""
    left_gain = np.sqrt(0.5 * (1 - p))
    right_gain = np.sqrt(0.5 * (1 + p))
    return np.stack([mono * left_gain, mono * right_gain], axis=-1)


def mix_into(buffer, sound, start_sample):
    sound = to_stereo(sound)
    end = start_sample + len(sound)
    if end <= 0 or start_sample >= len(buffer):
        return
    if start_sample < 0:
        sound = sound[-start_sample:]
        start_sample = 0
    if end > len(buffer):
        sound = sound[: len(buffer) - start_sample]
        end = len(buffer)
    buffer[start_sample:end] += sound


def midi_freq(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


def lowpass(audio, cutoff_hz, sr=SR):
    """One-pole IIR lowpass. cutoff_hz may be a scalar or a per-sample array,
    which lets a note's filter cutoff sweep over time (acid/pluck character)."""
    n = len(audio)
    cutoff = np.full(n, cutoff_hz, dtype=float) if np.isscalar(cutoff_hz) else cutoff_hz
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff / sr)
    out = np.empty_like(audio)
    acc = 0.0
    for i in range(n):
        acc += alpha[i] * (audio[i] - acc)
        out[i] = acc
    return out


# ---------------------------------------------------------------------------
# Laser sound effect
# ---------------------------------------------------------------------------

def synth_laser():
    duration = 0.16
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    f0, f1 = 1400.0, 180.0
    freq = f0 * (f1 / f0) ** (t / duration)  # exponential downward sweep
    phase = 2 * np.pi * np.cumsum(freq) / SR
    tone = np.sign(np.sin(phase))  # square wave: harsh sci-fi zap

    env = np.exp(-10.0 * t / duration)
    audio = tone * env
    audio = fade_edges(audio, 16)
    audio = audio / (np.max(np.abs(audio)) or 1.0) * 0.9
    return audio


# ---------------------------------------------------------------------------
# Fail sound effect (a word reaches the bottom in Normal mode)
# ---------------------------------------------------------------------------

def synth_fail():
    """A dull, low 'errr' buzzer — a wrong-answer sound, not a harsh alarm."""
    duration = 0.4
    n = int(SR * duration)
    t = np.linspace(0, duration, n, endpoint=False)

    f0 = 110.0
    saw1 = 2.0 * (t * f0 - np.floor(0.5 + t * f0))
    saw2 = 2.0 * (t * (f0 * 0.94) - np.floor(0.5 + t * (f0 * 0.94)))  # detuned: dissonant beat
    tone = 0.6 * saw1 + 0.6 * saw2

    buzz = 1.0 + 0.3 * np.sin(2 * np.pi * 35.0 * t)  # tremolo buzzer texture

    attack = max(1, int(SR * 0.01))
    release = max(1, int(SR * 0.15))
    env = np.ones(n)
    env[:attack] = np.linspace(0.0, 1.0, attack)
    env[-release:] *= np.linspace(1.0, 0.0, release)

    audio = tone * buzz * env
    audio = lowpass(audio, 2500.0)  # dull the harshness for a kids' game
    audio = fade_edges(audio, 16)
    audio = audio / (np.max(np.abs(audio)) or 1.0) * 0.85
    return audio


# ---------------------------------------------------------------------------
# Trance backing track
# ---------------------------------------------------------------------------

# One chord per bar: i - VI - III - VII in A minor (classic uplifting trance
# progression). Each entry is (bass root MIDI note, [chord tone MIDI notes]).
CHORDS = [
    (45, [57, 60, 64, 69]),  # Am : bass A2, arp/pad A3 C4 E4 A4
    (41, [53, 57, 60, 65]),  # F  : bass F2, arp/pad F3 A3 C4 F4
    (48, [60, 64, 67, 72]),  # C  : bass C3, arp/pad C4 E4 G4 C5
    (43, [55, 59, 62, 67]),  # G  : bass G2, arp/pad G3 B3 D4 G4
]


def make_kick(dur=0.28):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freq = 160.0 * (42.0 / 160.0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    tone = np.sin(phase)
    env = np.exp(-14.0 * t / dur)
    click = np.exp(-500.0 * t) * (np.random.rand(n) * 2 - 1) * 0.35
    return fade_edges(tone * env + click, 8)


def make_hat(dur=0.05):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.rand(n) * 2 - 1
    env = np.exp(-45.0 * t / dur)
    return fade_edges(lowpass(noise, 9000.0) * env * 0.55, 8)


def make_open_hat(dur=0.22):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    noise = np.random.rand(n) * 2 - 1
    env = np.exp(-9.0 * t / dur)
    return fade_edges(lowpass(noise, 9500.0) * env * 0.4, 8)


def make_pluck(freq, dur):
    """Bright, quickly-decaying saw — used for the rolling 16th-note arp."""
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    saw = 2.0 * (t * freq - np.floor(0.5 + t * freq))
    env = np.exp(-14.0 * t / dur)
    tone = lowpass(saw, 4200.0) * env
    return fade_edges(tone, 8)


def make_bass_pluck(freq, dur):
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    saw = 2.0 * (t * freq - np.floor(0.5 + t * freq))
    env = np.exp(-6.0 * t / dur)
    cutoff_env = 250.0 + 900.0 * np.exp(-8.0 * t / dur)  # slight acid-style sweep
    tone = lowpass(saw, cutoff_env) * env
    return fade_edges(tone, 8)


def make_pad_chord(freqs, dur):
    """Supersaw-ish sustained pad: 3 detuned sine layers per chord tone."""
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    detunes = (-0.006, 0.0, 0.006)
    mono = np.zeros(n)
    for f in freqs:
        for d in detunes:
            mono += np.sin(2 * np.pi * f * (1 + d) * t)
    mono /= len(freqs) * len(detunes)

    attack = max(1, int(SR * 0.05))
    release = max(1, int(SR * 0.4))
    env = np.ones(n)
    env[:attack] = np.linspace(0.0, 1.0, attack)
    env[-release:] *= np.linspace(1.0, 0.0, release)

    return lowpass(mono, 3200.0) * env


def make_duck_envelope(n_samples, kick_times, depth=0.75, recover=0.28):
    """Sidechain 'pump': a deep dip right on each kick that recovers over
    `recover` seconds — the signature breathing trance pads/bass sit under."""
    env = np.ones(n_samples)
    recover_samples = int(recover * SR)
    curve = 1.0 - depth * np.exp(-np.linspace(0, 6, recover_samples))
    for t0 in kick_times:
        start = int(t0 * SR)
        end = min(n_samples, start + recover_samples)
        length = end - start
        if length > 0:
            env[start:end] = np.minimum(env[start:end], curve[:length])
    return env


def synth_music_loop():
    bpm = 132.0
    beat = 60.0 / bpm
    beats_per_bar = 4
    bars = len(CHORDS)
    sixteenth = beat / 4.0
    loop_dur = beat * beats_per_bar * bars
    n = int(SR * loop_dur)

    drums = np.zeros((n, 2))
    melodic = np.zeros((n, 2))

    kick_snd = make_kick()
    hat_closed = make_hat()
    hat_open = make_open_hat()

    kick_times = []
    for bar in range(bars):
        bar_t0 = bar * beats_per_bar * beat
        for b in range(beats_per_bar):
            t0 = bar_t0 + b * beat
            kick_times.append(t0)
            mix_into(drums, kick_snd * 0.9, int(t0 * SR))
            mix_into(drums, pan(hat_closed * 0.5, 0.15), int((t0 + beat * 0.5) * SR))
        mix_into(drums, pan(hat_open * 0.4, -0.15), int((bar_t0 + 15 * sixteenth) * SR))

    # Bassline: plucks on the off-beat, bouncing against the kick.
    for bar in range(bars):
        bass_root_midi, _ = CHORDS[bar]
        freq = midi_freq(bass_root_midi)
        bar_t0 = bar * beats_per_bar * beat
        for b in range(beats_per_bar):
            t0 = bar_t0 + b * beat + beat * 0.5
            mix_into(melodic, make_bass_pluck(freq, beat * 0.9) * 0.6, int(t0 * SR))

    # Rolling 16th-note arpeggio, cycling this bar's chord tones, panned
    # side to side for movement.
    step_index = 0
    for bar in range(bars):
        _, tones = CHORDS[bar]
        bar_t0 = bar * beats_per_bar * beat
        for s in range(16):
            t0 = bar_t0 + s * sixteenth
            freq = midi_freq(tones[step_index % len(tones)])
            p = -0.3 if step_index % 2 == 0 else 0.3
            note = make_pluck(freq, sixteenth * 0.9)
            mix_into(melodic, pan(note * 0.22, p), int(t0 * SR))
            step_index += 1

    # Sustained supersaw pad, one chord per bar.
    for bar in range(bars):
        _, tones = CHORDS[bar]
        chord_freqs = [midi_freq(m) for m in tones[:3]]
        t0 = bar * beats_per_bar * beat
        pad = make_pad_chord(chord_freqs, beat * beats_per_bar * 0.98)
        mix_into(melodic, pan(pad * 0.35, 0.0), int(t0 * SR))

    duck_env = make_duck_envelope(n, kick_times)
    melodic *= duck_env[:, None]

    master = drums + melodic
    master = master / (np.max(np.abs(master)) or 1.0) * 0.85
    master = fade_edges(master, 64)  # click-free seam for the loop point
    return master


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    np.random.seed(42)

    laser = synth_laser()
    write_wav(os.path.join(OUT_DIR, "laser.wav"), laser)
    print("wrote sounds/laser.wav", f"({len(laser) / SR:.3f}s)")

    fail = synth_fail()
    write_wav(os.path.join(OUT_DIR, "fail.wav"), fail)
    print("wrote sounds/fail.wav", f"({len(fail) / SR:.3f}s)")

    music = synth_music_loop()
    write_wav(os.path.join(OUT_DIR, "music_loop.wav"), music, channels=2)
    print("wrote sounds/music_loop.wav", f"({len(music) / SR:.3f}s)")


if __name__ == "__main__":
    main()
