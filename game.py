"""
Kinder Type — a beginner typing game.

Old-school Asteroids-style ship shooting lasers at letters and words.

Modes:
    Beginner — a single stationary word is shown; a keyboard panel below
        the play area highlights (blinking red) the next key to press.
    Normal   — words fall from the top with increasing speed; destroy them
        before they reach the bottom or you lose a life.

Controls:
    Type the letters of the highlighted (yellow) target word/letter.
    Esc returns to the mode-select menu (quits from the menu itself).
    Any key advances past the Game Over screen back to the menu.
"""

import io
import math
import os
import queue
import random
import subprocess
import sys
import tempfile
import threading
from collections import deque

import pygame

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCREEN_W = 900
MAIN_H = 700     # play area height
KEYBOARD_H = 220  # beginner-mode keyboard panel height
FPS = 60

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "logo.png")
VOICE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "voices", "en_US-amy-medium.onnx",
)
AUDIO_SR = 44100
MUSIC_VOLUME = 0.35

BG_COLOR = (5, 5, 15)
SHIP_COLOR = (200, 220, 255)
LASER_COLOR = (255, 60, 60)
TEXT_COLOR = (180, 180, 200)
TARGET_COLOR = (62, 226, 83)  # #3ee253, matches patrickhenson.github.io's title green
HUD_COLOR = (120, 220, 140)
GAME_OVER_COLOR = (255, 80, 80)
MENU_TITLE_COLOR = TARGET_COLOR
MENU_OPTION_COLOR = (180, 180, 200)

KEYBOARD_BG = (0, 0, 0)
KEYBOARD_OUTLINE = (255, 255, 255)
KEYBOARD_LETTER = (255, 255, 255)
KEYBOARD_BLINK = (255, 40, 40)
BLINK_PERIOD_MS = 300

TOP_BAR_H = 44  # keeps falling words clear of the score/lives HUD
TOP_BAR_BG = (10, 10, 25)
TOP_BAR_BORDER = (60, 60, 90)

SHIP_RADIUS = 22
LASER_SPEED = 900.0  # px/sec
LASER_BOLT_LEN = 22  # short, so each keystroke's shot reads as a distinct bolt
FALL_SPEED_START = 35.0  # px/sec
FALL_SPEED_MAX = 140.0
SPAWN_INTERVAL_START = 1.6  # seconds
SPAWN_INTERVAL_MIN = 0.6
DIFFICULTY_RAMP_TIME = 600.0  # seconds to reach max difficulty
MAX_WORDS_START = 1
MAX_WORDS_END = 4

LIVES_START = 5

LETTER_POOL = list("abcdefghijklmnopqrstuvwxyz")
PUNCTUATION_POOL = list(".,!?'-")  # normal mode only; beginner never spawns these
NORMAL_CHAR_POOL = LETTER_POOL + PUNCTUATION_POOL

# Every 500 score, beginner mode unlocks the next word length (0 -> 3
# letters, 500 -> 3-4, 1000 -> 3-5, ...). Vocabulary is hand-curated,
# kid-appropriate, and leans STEM.
BEGINNER_SCORE_PER_LENGTH = 500
DICTIONARY_BY_LENGTH = {
    3: [
        "air", "ant", "arc", "arm", "art", "ash", "ask", "axe", "bag", "ban", "bar", "bat",
        "bay", "bed", "bee", "bet", "bib", "bid", "big", "bin", "bit", "bow", "box", "bud",
        "bug", "bun", "bus", "cab", "can", "cap", "car", "cat", "cog", "cop", "cot", "cow",
        "cry", "cub", "cup", "cut", "day", "den", "dew", "dig", "dip", "doe", "dog", "dot",
        "dry", "ear", "eat", "egg", "elf", "elk", "eye", "fan", "fat", "fig", "fin", "fit",
        "fix", "fly", "fog", "fox", "fun", "gap", "gas", "gem", "gum", "gun", "guy", "gym",
        "ham", "hat", "hen", "hip", "hit", "hog", "hop", "hot", "how", "hub", "hug", "hut",
        "ice", "icy", "ink", "jam", "jar", "jaw", "jet", "job", "jog", "joy", "jug", "keg",
        "key", "kid", "kit", "lab", "lad", "lap", "law", "leg", "lid", "lip", "lit", "lot",
        "map", "mat", "mix", "mob", "mud", "mug", "nap", "net", "new", "nod", "nut", "oak",
        "oar", "odd", "ohm", "oil", "one", "orb", "owl", "pad", "pan", "paw", "pea", "peg",
        "pen", "pet", "pie", "pig", "pin", "pit", "pod", "pop", "pot", "pub", "pug", "pun",
        "pup", "rag", "ram", "rat", "raw", "red", "rib", "rid", "rim", "rip", "rob", "rod",
        "rot", "row", "rub", "rug", "run", "sap", "saw", "sea", "set", "sew", "shy", "sip",
        "sit", "six", "ski", "sky", "son", "soy", "spa", "spy", "sub", "sum", "sun", "tab",
        "tag", "tan", "tap", "tea", "ten", "tie", "tin", "tip", "toe", "ton", "top", "toy",
        "tub", "tug", "two", "urn", "use", "van", "vat", "vet", "wag", "wax", "web", "wet",
        "wig", "win", "wit", "won", "yam", "zip", "zoo"
    ],
    4: [
        "arch", "arms", "back", "bake", "ball", "barn", "bean", "bear", "beef", "beet",
        "bike", "bird", "blue", "boat", "bolt", "bone", "book", "cake", "calf", "calm",
        "camp", "cave", "chop", "clap", "claw", "coin", "cold", "cone", "cook", "cool",
        "corn", "crab", "crow", "cube", "cyan", "deer", "desk", "dice", "disk", "dive",
        "dome", "door", "drag", "draw", "drum", "duck", "dust", "ears", "easy", "eyes",
        "face", "farm", "fast", "file", "fins", "fish", "five", "flag", "fold", "foot",
        "fort", "four", "frog", "gale", "game", "gate", "gear", "gill", "glow", "goat",
        "gold", "gram", "gray", "grow", "gust", "hail", "hair", "hand", "hard", "haul",
        "hawk", "haze", "head", "herb", "hide", "hike", "hive", "hour", "inch", "iris",
        "iron", "jeep", "jump", "kale", "kick", "kite", "kiwi", "knee", "lake", "lamb",
        "lamp", "land", "leaf", "leap", "leek", "legs", "lift", "limb", "lime", "line",
        "lion", "lock", "loud", "lung", "mars", "melt", "mile", "milk", "mist", "moon",
        "mule", "nail", "navy", "neck", "nest", "nine", "nose", "okra", "open", "oval",
        "oven", "page", "palm", "paws", "pear", "peel", "pink", "pint", "pipe", "play",
        "plum", "pond", "pork", "pour", "pull", "push", "raft", "rain", "ramp", "read",
        "rice", "ring", "rock", "roll", "room", "root", "rope", "rust", "sail", "sand",
        "seal", "seed", "seek", "shed", "shin", "ship", "silo", "sing", "sink", "skin",
        "skip", "sled", "slow", "snap", "snow", "soft", "song", "sort", "soup", "spin",
        "star", "stir", "surf", "swan", "swim", "tail", "talk", "tall", "taxi", "teal",
        "tent", "tram", "tree", "vein", "vise", "volt", "wake", "walk", "wall", "warm",
        "wasp", "watt", "wave", "week", "wind", "wing", "wink", "wire", "wolf", "worm",
        "wrap", "yard", "zero", "zoom"
    ],
    5: [
        "amber", "ankle", "apple", "arena", "awake", "bacon", "beach", "beige", "bison",
        "black", "blend", "blink", "blood", "bloom", "brain", "bread", "brown", "brush",
        "buggy", "build", "bumpy", "bunny", "cabin", "camel", "candy", "canoe", "carry",
        "carve", "catch", "chase", "cheek", "chest", "chick", "clamp", "clean", "climb",
        "clock", "close", "cloud", "comet", "coral", "count", "dance", "diver", "dozen",
        "dream", "dress", "drift", "drill", "drink", "dryer", "eagle", "earth", "eight",
        "elbow", "fence", "field", "fifty", "float", "foggy", "frost", "fruit", "funny",
        "fuzzy", "gecko", "gland", "glide", "grape", "grass", "green", "guava", "happy",
        "heart", "hertz", "horse", "house", "hover", "humid", "hyena", "igloo", "ivory",
        "joule", "juice", "kayak", "knead", "koala", "laugh", "learn", "lemon", "level",
        "lever", "liter", "llama", "mango", "melon", "meter", "misty", "mixer", "month",
        "moose", "motor", "mouse", "mouth", "muggy", "music", "nerve", "ocean", "onion",
        "orbit", "organ", "otter", "ounce", "paint", "panda", "paper", "peach", "pedal",
        "petal", "piano", "pilot", "plane", "plant", "pluto", "pound", "prism", "pupil",
        "puppy", "quart", "quiet", "radio", "rainy", "reach", "rhino", "river", "robot",
        "rover", "ruler", "screw", "seven", "shake", "shape", "shark", "sheep", "shell",
        "shine", "shiny", "shore", "short", "skate", "skull", "skunk", "sleep", "sleet",
        "slice", "slide", "smile", "snail", "snake", "solar", "space", "speed", "spine",
        "squid", "steak", "steer", "stone", "stork", "storm", "stove", "sugar", "sunny",
        "sweat", "swing", "thigh", "think", "three", "throw", "thumb", "tiger", "timer",
        "toast", "tooth", "tower", "train", "truck", "venus", "voice", "wagon", "waist",
        "water", "wedge", "weigh", "whale", "wheel", "white", "windy", "wrist", "zebra"
    ],
    6: [
        "anchor", "artery", "artist", "ascend", "author", "autumn", "badger", "bakery",
        "banana", "basket", "beaver", "beetle", "bounce", "breeze", "bridge", "bright",
        "bronze", "bubble", "bucket", "bunker", "burger", "button", "candle", "carrot",
        "castle", "celery", "cherry", "chilly", "chisel", "circle", "cloudy", "cookie",
        "cooler", "copper", "cornea", "cosmos", "cousin", "crayon", "create", "decade",
        "degree", "desert", "design", "doctor", "donkey", "dragon", "eleven", "engine",
        "eyelid", "falcon", "family", "farmer", "father", "forest", "freeze", "fridge",
        "friend", "frosty", "gadget", "galaxy", "gallon", "garage", "garlic", "gather",
        "gazebo", "gentle", "giggle", "giggly", "glider", "gopher", "guitar", "hammer",
        "heater", "hiking", "hotdog", "indigo", "invent", "jackal", "jaguar", "jigsaw",
        "juggle", "jungle", "kelvin", "kettle", "kidney", "kitten", "launch", "letter",
        "lizard", "magnet", "magpie", "mallet", "market", "maroon", "meadow", "melody",
        "meteor", "minute", "mirror", "monkey", "mother", "muscle", "museum", "nebula",
        "newton", "number", "orange", "oyster", "paddle", "palace", "papaya", "parrot",
        "pascal", "peanut", "pelvis", "pencil", "pepper", "pickup", "picnic", "pigeon",
        "pillow", "planet", "pliers", "possum", "potato", "puddle", "pulley", "purple",
        "puzzle", "python", "rabbit", "radish", "ranger", "raptor", "retina", "rhythm",
        "riddle", "ripple", "rocket", "router", "rowing", "sailor", "salami", "salmon",
        "sander", "saturn", "school", "sculpt", "search", "season", "second", "seesaw",
        "sensor", "shadow", "shower", "shrimp", "silver", "sister", "sketch", "skiing",
        "socket", "speedy", "sphere", "spider", "spiral", "splash", "spring", "sprout",
        "square", "squash", "stairs", "sticky", "stormy", "stream", "stripy", "strong",
        "summer", "sunset", "symbol", "temple", "tendon", "thirty", "tinker", "tongue",
        "tunnel", "turkey", "turnip", "turtle", "twelve", "twenty", "unwrap", "uranus",
        "vacuum", "violet", "violin", "walrus", "washer", "weasel", "wiggly", "window",
        "winter", "wonder", "wrench", "yellow"
    ],
    7: [
        "abdomen", "airship", "anemone", "apricot", "avocado", "balance", "balcony",
        "battery", "bedroom", "bicycle", "billion", "biology", "bladder", "blanket",
        "blender", "boating", "brother", "buffalo", "builder", "bulldog", "cabbage",
        "calorie", "camping", "carrier", "catfish", "celsius", "century", "cheetah",
        "chemist", "chicken", "chimney", "chuckle", "circuit", "climate", "coconut",
        "collect", "compass", "cottage", "cricket", "crimson", "crowbar", "cruiser",
        "crystal", "cyclone", "dentist", "diamond", "dolphin", "drizzle", "drought",
        "eardrum", "earlobe", "eclipse", "evening", "explore", "eyebrow", "eyelash",
        "feather", "firefly", "fishing", "forearm", "freezer", "frisbee", "geology",
        "giraffe", "gorilla", "gravity", "hacksaw", "hallway", "hammock", "hamster",
        "harvest", "hexagon", "hundred", "imagine", "kitchen", "kneecap", "knuckle",
        "ladybug", "lantern", "leopard", "lettuce", "library", "lobster", "machine",
        "magenta", "mammoth", "manatee", "mansion", "measure", "meerkat", "mercury",
        "million", "minivan", "monsoon", "morning", "mustang", "narwhal", "neptune",
        "observe", "octagon", "octopus", "ostrich", "panther", "parsnip", "pattern",
        "peacock", "pelican", "penguin", "physics", "plumber", "polygon", "popcorn",
        "printer", "pumpkin", "pyramid", "raccoon", "rainbow", "ratchet", "reptile",
        "ribcage", "rooftop", "rooster", "sailing", "sandbox", "sausage", "scarlet",
        "science", "scooter", "shuttle", "skating", "snorkel", "sparkle", "sparkly",
        "sparrow", "speaker", "spinach", "squeeze", "stadium", "stapler", "stomach",
        "sunrise", "surfing", "surgeon", "tadpole", "teacher", "termite", "theater",
        "thunder", "toaster", "toenail", "toolbox", "tornado", "tractor", "trolley",
        "trumpet", "typhoon", "ukulele", "village", "volcano", "vulture", "weather",
        "whisper", "whistle", "whittle", "wildcat"
    ],
    8: [
        "airplane", "alphabet", "anteater", "aqueduct", "assemble", "assembly", "asteroid",
        "backpack", "backyard", "barbecue", "birthday", "blizzard", "broccoli", "calendar",
        "campfire", "campsite", "cardinal", "chipmunk", "cockatoo", "computer", "cucumber",
        "cylinder", "daylight", "dinosaur", "discover", "doghouse", "downpour", "eggplant",
        "elephant", "elevator", "engineer", "explorer", "flamingo", "forecast", "forehead",
        "fountain", "goldfish", "hardware", "heatwave", "hedgehog", "hospital", "housefly",
        "inventor", "kangaroo", "keyboard", "kilogram", "ladybird", "lavender", "ligament",
        "mandarin", "meatball", "mechanic", "midnight", "mongoose", "monorail", "monument",
        "moonwalk", "mountain", "mulberry", "navigate", "notebook", "overcast", "paddling",
        "pangolin", "pavilion", "pentagon", "polliwog", "question", "raindrop", "recorder",
        "reindeer", "robotics", "sailboat", "sandwich", "scorpion", "seahorse", "seashell",
        "shoulder", "skeleton", "snowplow", "software", "songbird", "squirrel", "stardust",
        "starfish", "stingray", "sunlight", "sunshine", "teaspoon", "tortoise", "triangle",
        "tricycle", "umbrella", "unicycle", "universe", "windmill", "zeppelin", "zucchini"
    ],
    9: [
        "albatross", "alligator", "ambulance", "armadillo", "artichoke", "asparagus",
        "astronaut", "astronomy", "avalanche", "barometer", "billboard", "birdhouse",
        "blueberry", "blueprint", "bulldozer", "bumblebee", "butterfly", "calculate",
        "cardboard", "cartilage", "cathedral", "centipede", "chameleon", "chemistry",
        "chihuahua", "classroom", "clubhouse", "construct", "cosmonaut", "cranberry",
        "crocodile", "curiosity", "dalmatian", "dashboard", "discovery", "dragonfly",
        "drumstick", "earthworm", "farmhouse", "firehouse", "fireplace", "firetruck",
        "freighter", "gearwheel", "generator", "groundhog", "hurricane", "hydraulic",
        "invention", "jellybean", "jellyfish", "kilometer", "lightning", "mechanism",
        "microwave", "moonlight", "orangutan", "pineapple", "playhouse", "porcupine",
        "prototype", "raspberry", "rectangle", "satellite", "scientist", "snowboard",
        "snowflake", "spaceship", "spacesuit", "spacewalk", "spaghetti", "speedboat",
        "staircase", "starfruit", "starlight", "stopwatch", "structure", "submarine",
        "sunflower", "sunscreen", "surfboard", "tangerine", "tarantula", "telescope",
        "toadstool", "trapezoid", "treehouse", "turquoise", "warehouse", "waterfall",
        "wolverine"
    ],
    10: [
        "atmosphere", "binoculars", "blackberry", "calculator", "centimeter", "chalkboard",
        "chinchilla", "courthouse", "dishwasher", "earthquake", "experiment", "fahrenheit",
        "fingernail", "flashlight", "friendship", "grapefruit", "helicopter", "humidifier",
        "innovation", "jackrabbit", "laboratory", "lighthouse", "locomotive", "microscope",
        "milliliter", "millimeter", "motorcycle", "nightlight", "playground", "rhinoceros",
        "salamander", "skateboard", "skyscraper", "spacecraft", "strawberry", "tablespoon",
        "technology", "television", "thermostat", "trampoline", "watermelon", "woodpecker",
        "wristwatch"
    ],
    11: [
        "calculation", "caterpillar", "cauliflower", "electricity", "exploration",
        "firefighter", "grandfather", "grandmother", "grasshopper", "hummingbird",
        "imagination", "investigate", "mathematics", "mockingbird", "observation",
        "observatory", "pterodactyl", "rattlesnake", "schoolhouse", "screwdriver",
        "stegosaurus", "temperature", "triceratops", "underground"
    ],
    12: [
        "brontosaurus", "hippopotamus", "interstellar", "kindergarten", "refrigerator",
        "thunderstorm", "velociraptor"
    ],
    13: [
        "archaeologist", "constellation", "tyrannosaurus"
    ],
}
BEGINNER_MAX_WORD_LENGTH = max(DICTIONARY_BY_LENGTH)

# Normal mode's word pool: the same dictionary, flattened.
ALL_WORDS = [w for words in DICTIONARY_BY_LENGTH.values() for w in words]

BEGINNER_WORD_Y = TOP_BAR_H + (MAIN_H - TOP_BAR_H) * 0.35
BEGINNER_COMPLETE_DELAY = 0.2  # seconds to pause after finishing a word

# FIFO of recent picks, filtered out when choosing the next one, so the
# same word/letter doesn't reappear too soon. Sized under each mode's
# smallest active pool so there's always real variety left to draw from.
RECENT_WORDS_HISTORY = 10  # beginner: well under the 20-word 3-letter tier
NORMAL_RECENT_HISTORY = max(15, round(len(ALL_WORDS) * 0.05))  # normal: scales with the dictionary

KEY_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]


class FallingWord:
    """A single letter or word, falling (fall_speed > 0) or stationary."""

    def __init__(self, text, x, y, fall_speed):
        self.text = text
        self.x = x
        self.y = y
        self.fall_speed = fall_speed
        self.typed = 0  # how many leading chars have been matched

    def remaining(self):
        return self.text[self.typed:]

    def is_complete(self):
        return self.typed >= len(self.text)


class Laser:
    """A projectile fired from the ship toward a target position."""

    def __init__(self, start_pos, target_pos):
        self.x, self.y = start_pos
        dx = target_pos[0] - start_pos[0]
        dy = target_pos[1] - start_pos[1]
        dist = math.hypot(dx, dy) or 1.0
        self.vx = dx / dist * LASER_SPEED
        self.vy = dy / dist * LASER_SPEED
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -50 or self.x > SCREEN_W + 50 or self.y < -50 or self.y > MAIN_H + 50:
            self.alive = False


def draw_ship(surface, center, angle_rad):
    """Draw a simple Asteroids-style polygon rocket ship pointing at angle_rad."""
    cx, cy = center
    nose = (0, -SHIP_RADIUS)
    left_wing = (-SHIP_RADIUS * 0.7, SHIP_RADIUS * 0.8)
    left_notch = (-SHIP_RADIUS * 0.25, SHIP_RADIUS * 0.35)
    right_notch = (SHIP_RADIUS * 0.25, SHIP_RADIUS * 0.35)
    right_wing = (SHIP_RADIUS * 0.7, SHIP_RADIUS * 0.8)
    points = [nose, left_wing, left_notch, right_notch, right_wing]

    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rotated = []
    for px, py in points:
        rx = px * cos_a - py * sin_a
        ry = px * sin_a + py * cos_a
        rotated.append((cx + rx, cy + ry))

    pygame.draw.polygon(surface, SHIP_COLOR, rotated, width=2)


def pick_new_text(existing_texts, recent_texts=(), score=0):
    """Pick a letter/punctuation mark or word not already falling or recently
    used. Single characters get rarer as score rises (50% chance at score 0,
    tapering to a 10% floor by score 3000)."""
    letter_chance = max(0.1, 0.5 - (score / 3000) * 0.4)
    use_word = random.random() >= letter_chance
    pool = ALL_WORDS if use_word else NORMAL_CHAR_POOL
    avoid = set(existing_texts) | set(recent_texts)
    choices = [t for t in pool if t not in avoid]
    if not choices:
        choices = [t for t in pool if t not in existing_texts]
    if not choices:
        choices = pool
    return random.choice(choices)


class SpeechEngine:
    """Background text-to-speech backed by one long-lived `piper` CLI process.

    piper runs as a subprocess, never imported as a library, so this
    project's own license isn't bound by piper-tts's GPL-3.0 — an external
    GPL tool run as a separate process is aggregation, not linking. One
    process stays alive for the whole session (loading the voice model
    once) and is fed one line of text per utterance via stdin; reloading
    the model per call caused a noticeable per-word delay. piper logs
    "Wrote <path>" to stderr per line, in send order — a reader thread uses
    that to pick up each finished WAV and queue it for poll() to play.
    """

    def __init__(self, voice_path):
        self.voice_path = voice_path
        self.piper_bin = os.path.join(os.path.dirname(sys.executable), "piper")
        self.enabled = os.path.isfile(self.piper_bin) and os.path.isfile(voice_path)
        self._work_queue = queue.Queue()
        self._ready_queue = queue.Queue()
        self._proc = None
        self._out_dir = None
        if self.enabled:
            try:
                self._out_dir = tempfile.mkdtemp(prefix="kindertype_tts_")
                self._proc = subprocess.Popen(
                    [
                        self.piper_bin, "-m", self.voice_path,
                        "-d", self._out_dir, "--output-dir-naming", "timestamp",
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                threading.Thread(target=self._writer, daemon=True).start()
                threading.Thread(target=self._reader, daemon=True).start()
            except Exception:
                self.enabled = False

    def say(self, text):
        if self.enabled:
            self._work_queue.put(text)

    def shutdown(self):
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except Exception:
                pass
            try:
                self._proc.terminate()
            except Exception:
                pass
        if self._out_dir is not None:
            import shutil
            shutil.rmtree(self._out_dir, ignore_errors=True)

    def _writer(self):
        while True:
            text = self._work_queue.get()
            try:
                self._proc.stdin.write(text.replace("\n", " ") + "\n")
                self._proc.stdin.flush()
            except Exception:
                return

    def _reader(self):
        prefix = "INFO:__main__:Wrote "
        try:
            for line in self._proc.stderr:
                line = line.strip()
                if not line.startswith(prefix):
                    continue
                path = line[len(prefix):]
                try:
                    with open(path, "rb") as f:
                        self._ready_queue.put(f.read())
                except OSError:
                    pass
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        except Exception:
            pass

    def poll(self, muted=False):
        """Play any speech clips that finished synthesizing. Call once per frame."""
        while True:
            try:
                wav_bytes = self._ready_queue.get_nowait()
            except queue.Empty:
                return
            try:
                snd = pygame.mixer.Sound(io.BytesIO(wav_bytes))
                snd.set_volume(0.0 if muted else 1.0)
                snd.play()
            except pygame.error:
                pass


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.display.set_icon(pygame.image.load(LOGO_PATH))
        except (pygame.error, FileNotFoundError):
            pass
        self.init_audio()
        self.speech = SpeechEngine(VOICE_PATH)
        pygame.display.set_caption("Kinder Type")
        self.screen = pygame.display.set_mode((SCREEN_W, MAIN_H))
        self.clock = pygame.time.Clock()
        self.font_word = pygame.font.SysFont("dejavusansmono", 32)
        self.font_target = pygame.font.SysFont("dejavusansmono", 48)
        self.font_hud = pygame.font.SysFont("dejavusansmono", 24)
        self.font_big = pygame.font.SysFont("dejavusansmono", 64)
        self.font_menu_title = pygame.font.SysFont("dejavusansmono", 56)
        self.font_menu_option = pygame.font.SysFont("dejavusansmono", 30)
        self.font_menu_badge = pygame.font.SysFont("dejavusansmono", 30, bold=True)
        self.font_key = pygame.font.SysFont("dejavusansmono", 26)

        self.logo_image = None
        try:
            logo = pygame.image.load(LOGO_PATH).convert_alpha()
            badge_h = 28
            badge_w = round(badge_h * logo.get_width() / logo.get_height())
            self.logo_image = pygame.transform.smoothscale(logo, (badge_w, badge_h))
        except (pygame.error, FileNotFoundError):
            pass

        self.state = "menu"  # "menu" | "playing" | "game_over"
        self.mode = None      # "beginner" | "normal"
        self.muted = False
        self.reset()
        self.speech.say("Welcome to Kinnder Type. Please select your difficulty mode by pressing one or two to start the game.")

    def toggle_mute(self):
        self.muted = not self.muted
        pygame.mixer.music.set_volume(0.0 if self.muted else MUSIC_VOLUME)
        for sound in (self.laser_sound, self.fail_sound):
            if sound is not None:
                sound.set_volume(0.0 if self.muted else 1.0)

    # -- setup -------------------------------------------------------------

    def init_audio(self):
        self.laser_sound = None
        self.fail_sound = None
        try:
            pygame.mixer.init(frequency=AUDIO_SR, size=-16, channels=2)
            self.laser_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "laser.wav"))
            self.fail_sound = pygame.mixer.Sound(os.path.join(SOUNDS_DIR, "fail.wav"))
            pygame.mixer.music.load(os.path.join(SOUNDS_DIR, "music_loop.wav"))
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            pygame.mixer.music.play(loops=-1)
        except pygame.error:
            pass  # no audio device available; game still runs silently

    def reset(self):
        self.ship_pos = (SCREEN_W // 2, MAIN_H - 60)
        self.ship_angle = 0.0
        self.words = []
        self.lasers = []
        self.spawn_timer = 0.0
        self.elapsed = 0.0
        self.score = 0
        self.lives = LIVES_START
        self.target = None  # currently locked FallingWord being typed
        self.game_over = False
        self.beginner_spawn_timer = 0.0  # counts down after a word is completed
        self.recent_words = deque(maxlen=RECENT_WORDS_HISTORY)
        self.recent_normal_texts = deque(maxlen=NORMAL_RECENT_HISTORY)

    def start_beginner(self):
        pygame.display.set_mode((SCREEN_W, MAIN_H + KEYBOARD_H))
        self.reset()
        self.mode = "beginner"
        self.state = "playing"
        self.spawn_beginner_word()

    def start_normal(self):
        pygame.display.set_mode((SCREEN_W, MAIN_H))
        self.reset()
        self.mode = "normal"
        self.state = "playing"

    def go_to_menu(self):
        pygame.display.set_mode((SCREEN_W, MAIN_H))
        self.state = "menu"
        self.mode = None

    # -- difficulty (normal mode) -------------------------------------------

    def difficulty_t(self):
        return min(1.0, self.elapsed / DIFFICULTY_RAMP_TIME)

    def current_fall_speed(self):
        t = self.difficulty_t()
        return FALL_SPEED_START + (FALL_SPEED_MAX - FALL_SPEED_START) * t

    def current_spawn_interval(self):
        t = self.difficulty_t()
        return SPAWN_INTERVAL_START + (SPAWN_INTERVAL_MIN - SPAWN_INTERVAL_START) * t

    def current_max_words(self):
        t = self.difficulty_t()
        return round(MAX_WORDS_START + (MAX_WORDS_END - MAX_WORDS_START) * t)

    def spawn_word(self):
        existing = {w.text for w in self.words}
        text = pick_new_text(existing, self.recent_normal_texts, self.score)
        self.recent_normal_texts.append(text)
        margin = 40
        half_w = self.font_word.size(text)[0] / 2
        min_x, max_x = margin + half_w, SCREEN_W - margin - half_w
        x = random.randint(round(min_x), round(max_x)) if min_x < max_x else SCREEN_W // 2
        self.words.append(FallingWord(text, x, TOP_BAR_H - 20.0, self.current_fall_speed()))

    def beginner_word_pool(self):
        max_len = min(
            BEGINNER_MAX_WORD_LENGTH,
            3 + self.score // BEGINNER_SCORE_PER_LENGTH,
        )
        pool = []
        for length, words in DICTIONARY_BY_LENGTH.items():
            if length <= max_len:
                pool.extend(words)
        return pool

    def spawn_beginner_word(self):
        pool = self.beginner_word_pool()
        choices = [w for w in pool if w not in self.recent_words] or pool
        text = random.choice(choices)
        word = FallingWord(text, SCREEN_W // 2, BEGINNER_WORD_Y, 0.0)
        self.words = [word]
        self.target = word
        self.speech.say(text)
        self.recent_words.append(text)

    # -- input ---------------------------------------------------------------

    def handle_key(self, char):
        if self.target is not None and self.target in self.words:
            expected = self.target.remaining()[:1]
            if expected == char:
                self.target.typed += 1
                self.fire_laser(self.target)
                if self.target.is_complete():
                    finished = self.target
                    self.destroy_word(finished)
                    self.target = None
                    if self.mode == "beginner":
                        self.beginner_spawn_timer = BEGINNER_COMPLETE_DELAY
                    elif self.mode == "normal":
                        self.speech.say(finished.text)
            return

        # No target locked yet (normal mode): find a word starting with this char.
        candidates = [w for w in self.words if w.remaining()[:1] == char]
        if not candidates:
            return
        candidates.sort(key=lambda w: -w.y)  # closest to the ship first
        chosen = candidates[0]
        chosen.typed += 1
        self.target = chosen
        self.fire_laser(chosen)
        if chosen.is_complete():
            self.destroy_word(chosen)
            self.target = None
            self.speech.say(chosen.text)

    def char_target_pos(self, word, index):
        """Screen position of the character at `index` within `word`'s rendered text."""
        font = self.font_target
        index = max(0, min(index, len(word.text) - 1))
        char_w = font.size("M")[0]  # monospace font: every glyph has this width
        total_w = char_w * len(word.text)
        start_x = word.x - total_w / 2
        x = start_x + char_w * index + char_w / 2
        y = word.y + font.get_height() / 2
        return (x, y)

    def fire_laser(self, word):
        if self.mode == "beginner":
            target_pos = self.char_target_pos(word, word.typed - 1)
        else:
            target_pos = (word.x, word.y)
        self.lasers.append(Laser(self.ship_pos, target_pos))
        dx = target_pos[0] - self.ship_pos[0]
        dy = target_pos[1] - self.ship_pos[1]
        self.ship_angle = math.atan2(dx, -dy)
        if self.laser_sound is not None:
            self.laser_sound.play()

    def destroy_word(self, word):
        if word in self.words:
            self.words.remove(word)
        self.score += len(word.text) * 10

    # -- update ----------------------------------------------------------------

    def update(self, dt):
        if self.state != "playing" or self.game_over:
            return

        self.elapsed += dt

        if self.mode == "beginner" and self.beginner_spawn_timer > 0.0:
            self.beginner_spawn_timer -= dt
            if self.beginner_spawn_timer <= 0.0:
                self.spawn_beginner_word()

        if self.mode == "normal":
            self.spawn_timer += dt
            can_spawn = len(self.words) < self.current_max_words()
            if can_spawn and self.spawn_timer >= self.current_spawn_interval():
                self.spawn_timer = 0.0
                self.spawn_word()

        for word in self.words:
            word.y += word.fall_speed * dt

        for laser in self.lasers:
            laser.update(dt)
        self.lasers = [l for l in self.lasers if l.alive]

        if self.mode == "normal":
            reached_bottom = [w for w in self.words if w.y >= MAIN_H - 40]
            for word in reached_bottom:
                self.words.remove(word)
                if word is self.target:
                    self.target = None
                self.lives -= 1
                if self.fail_sound is not None:
                    self.fail_sound.play()
                if self.lives <= 0:
                    self.game_over = True

    # -- draw --------------------------------------------------------------

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
            return

        self.screen.fill(BG_COLOR)
        self.draw_play_area()
        self.draw_top_bar()
        if self.mode == "beginner":
            self.draw_keyboard_panel()
        pygame.display.flip()

    def draw_menu(self):
        self.screen.fill(BG_COLOR)

        title_surf = self.font_menu_title.render("Kinder Type", True, MENU_TITLE_COLOR)
        title_rect = title_surf.get_rect(center=(SCREEN_W // 2, MAIN_H // 2 - 120))
        self.screen.blit(title_surf, title_rect)

        self.draw_menu_option("1", "Beginner Mode", MAIN_H // 2 - 10)
        self.draw_menu_option("2", "Normal Mode", MAIN_H // 2 + 60)

        mute_label = "M to unmute" if self.muted else "M to mute"
        hint = self.font_hud.render(f"Esc to quit   •   {mute_label}", True, TEXT_COLOR)
        hint_rect = hint.get_rect(center=(SCREEN_W // 2, MAIN_H // 2 + 140))
        self.screen.blit(hint, hint_rect)

        pygame.display.flip()

    def draw_menu_option(self, number, text, y):
        badge_size = 46
        gap = 16

        text_surf = self.font_menu_option.render(text, True, MENU_OPTION_COLOR)
        total_w = badge_size + gap + text_surf.get_width()
        start_x = (SCREEN_W - total_w) / 2

        badge_rect = pygame.Rect(start_x, y - badge_size / 2, badge_size, badge_size)
        pygame.draw.rect(self.screen, TARGET_COLOR, badge_rect, width=3, border_radius=8)
        num_surf = self.font_menu_badge.render(number, True, TARGET_COLOR)
        num_rect = num_surf.get_rect(center=badge_rect.center)
        self.screen.blit(num_surf, num_rect)

        text_rect = text_surf.get_rect(midleft=(start_x + badge_size + gap, y))
        self.screen.blit(text_surf, text_rect)

    def draw_play_area(self):
        word_font = self.font_target if self.mode == "beginner" else self.font_word

        for word in self.words:
            typed_part = word.text[:word.typed]
            rest_part = word.text[word.typed:]
            is_target = word is self.target

            typed_surf = word_font.render(typed_part, True, LASER_COLOR)
            rest_color = TARGET_COLOR if is_target else TEXT_COLOR
            rest_surf = word_font.render(rest_part, True, rest_color)

            total_w = typed_surf.get_width() + rest_surf.get_width()
            start_x = word.x - total_w // 2
            self.screen.blit(typed_surf, (start_x, word.y))
            self.screen.blit(rest_surf, (start_x + typed_surf.get_width(), word.y))

        for laser in self.lasers:
            dist = math.hypot(laser.vx, laser.vy) or 1.0
            dirx, diry = laser.vx / dist, laser.vy / dist
            tail = (laser.x - dirx * LASER_BOLT_LEN, laser.y - diry * LASER_BOLT_LEN)
            pygame.draw.line(self.screen, LASER_COLOR, tail, (laser.x, laser.y), width=3)

        draw_ship(self.screen, self.ship_pos, self.ship_angle)

        if self.game_over:
            play_center_y = TOP_BAR_H + (MAIN_H - TOP_BAR_H) // 2
            over_surf = self.font_big.render("GAME OVER", True, GAME_OVER_COLOR)
            rect = over_surf.get_rect(center=(SCREEN_W // 2, play_center_y - 20))
            self.screen.blit(over_surf, rect)
            hint_surf = self.font_hud.render(
                "Press any key to return to the menu", True, TEXT_COLOR,
            )
            hint_rect = hint_surf.get_rect(center=(SCREEN_W // 2, play_center_y + 40))
            self.screen.blit(hint_surf, hint_rect)

    def draw_top_bar(self):
        rect = pygame.Rect(0, 0, SCREEN_W, TOP_BAR_H)
        pygame.draw.rect(self.screen, TOP_BAR_BG, rect)
        pygame.draw.line(self.screen, TOP_BAR_BORDER, (0, TOP_BAR_H), (SCREEN_W, TOP_BAR_H), width=2)

        score_left = 16
        if self.logo_image is not None:
            logo_rect = self.logo_image.get_rect(midleft=(16, TOP_BAR_H // 2))
            self.screen.blit(self.logo_image, logo_rect)
            score_left = logo_rect.right + 10

        score_surf = self.font_hud.render(f"Score: {self.score}", True, HUD_COLOR)
        score_rect = score_surf.get_rect(midleft=(score_left, TOP_BAR_H // 2))
        self.screen.blit(score_surf, score_rect)

        if self.mode == "normal":
            lives_surf = self.font_hud.render(f"Lives: {self.lives}", True, HUD_COLOR)
            lives_rect = lives_surf.get_rect(midright=(SCREEN_W - 16, TOP_BAR_H // 2))
            self.screen.blit(lives_surf, lives_rect)

    def draw_keyboard_panel(self):
        panel_rect = pygame.Rect(0, MAIN_H, SCREEN_W, KEYBOARD_H)
        pygame.draw.rect(self.screen, KEYBOARD_BG, panel_rect)

        next_char = self.target.remaining()[:1] if self.target else None
        blink_on = (pygame.time.get_ticks() // BLINK_PERIOD_MS) % 2 == 0

        key_w, key_h, gap = 62, 52, 8
        row_offsets = [0, key_w * 0.5, key_w * 1.0]
        center_shift = row_offsets[-1] / 2
        row_y = MAIN_H + 20

        for row_index, row in enumerate(KEY_ROWS):
            row_width = len(row) * key_w + (len(row) - 1) * gap
            start_x = (SCREEN_W - row_width) / 2 + row_offsets[row_index] - center_shift
            y = row_y + row_index * (key_h + gap)
            for i, ch in enumerate(row):
                x = start_x + i * (key_w + gap)
                rect = pygame.Rect(x, y, key_w, key_h)
                is_next = ch == next_char
                color = KEYBOARD_BLINK if (is_next and blink_on) else KEYBOARD_OUTLINE
                pygame.draw.rect(self.screen, color, rect, width=2, border_radius=6)
                letter_color = KEYBOARD_BLINK if (is_next and blink_on) else KEYBOARD_LETTER
                letter_surf = self.font_key.render(ch.upper(), True, letter_color)
                letter_rect = letter_surf.get_rect(center=rect.center)
                self.screen.blit(letter_surf, letter_rect)

    # -- main loop -----------------------------------------------------------

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.speech.shutdown()
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "menu":
                            self.speech.shutdown()
                            pygame.quit()
                            sys.exit(0)
                        self.go_to_menu()
                        continue

                    if self.state == "menu":
                        if event.unicode == "1":
                            self.start_beginner()
                        elif event.unicode == "2":
                            self.start_normal()
                        elif event.key == pygame.K_m:
                            self.toggle_mute()
                    elif self.game_over:
                        self.go_to_menu()
                    elif self.state == "playing" and event.unicode and (
                        event.unicode.isalpha() or event.unicode in PUNCTUATION_POOL
                    ):
                        self.handle_key(event.unicode.lower())

            self.update(dt)
            self.draw()
            self.speech.poll(self.muted)


if __name__ == "__main__":
    Game().run()
