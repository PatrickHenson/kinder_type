// Kinder Type — browser port of game.py. Static: no server logic, speech is pre-rendered mp3.
"use strict";

const SCREEN_W = 900, MAIN_H = 700, KEYBOARD_H = 250;
const MUSIC_VOLUME = 0.28, SFX_VOLUME = 0.8;
const TARGET = "#3ee253", TEXT = "#b4b4c8", LASER = "#ff3c3c", HUD = "#78dc8c", OVER = "#ff5050";
const BLINK = "#ff2828", WHITE = "#ffffff", INERT_OUT = "#505064", INERT_LET = "#5f5f73";
const BLINK_PERIOD_MS = 300, WRONG_FLASH = 0.25, SHAKE_PX = 8, SHAKE_HZ = 16;
const TOP_BAR_H = 44, SHIP_RADIUS = 22, LASER_SPEED = 900, LASER_BOLT_LEN = 22;
const FALL_START = 35, FALL_MAX = 140, SPAWN_START = 1.6, SPAWN_MIN = 0.6, RAMP_TIME = 600;
const MAX_WORDS_START = 1, MAX_WORDS_END = 4, LIVES_START = 5;
const SCORE_PER_LENGTH = 500, RECENT_WORDS = 10, BEGINNER_DELAY = 0.2;
const BEGINNER_WORD_Y = TOP_BAR_H + (MAIN_H - TOP_BAR_H) * 0.35;
const LETTERS = "abcdefghijklmnopqrstuvwxyz".split("");
const PUNCT = [".", ",", "'", "-"];
const PUNCT_AUDIO = { ".": "p_period", ",": "p_comma", "'": "p_apostrophe", "-": "p_dash" };
const NORMAL_POOL = LETTERS.concat(PUNCT);
const FONT = '"DejaVu Sans Mono", Menlo, Consolas, "Liberation Mono", monospace';

const KEYBOARD_ROWS = [
  [["`",1],["1",1],["2",1],["3",1],["4",1],["5",1],["6",1],["7",1],["8",1],["9",1],["0",1],["-",1],["=",1],["Bksp",2]],
  [["Tab",1.5],["Q",1],["W",1],["E",1],["R",1],["T",1],["Y",1],["U",1],["I",1],["O",1],["P",1],["[",1],["]",1],["\\",1.5]],
  [["Caps",1.75],["A",1],["S",1],["D",1],["F",1],["G",1],["H",1],["J",1],["K",1],["L",1],[";",1],["'",1],["Enter",2.25]],
  [["Shift",2.25],["Z",1],["X",1],["C",1],["V",1],["B",1],["N",1],["M",1],[",",1],[".",1],["/",1],["Shift",2.75]],
  [["Ctrl",1.25],["Win",1.25],["Alt",1.25],["Space",7.5],["Alt",1.25],["Fn",1.25],["Ctrl",1.25]],
];
const ROW_UNITS = 15;

const canvas = document.getElementById("c");
const ctx = canvas.getContext("2d");
const logo = new Image(); logo.src = "logo.svg";

let dictionary = {};          // length -> [words]
let maxLen = 3;
let allWords = [];
let normalRecentMax = 15;

// ---------------------------------------------------------------- audio
let actx = null, musicGain, sfxGain, speechGain, musicSrc = null;
const buffers = {};           // url -> AudioBuffer | Promise
let muted = false;

function loadBuffer(url) {
  if (!actx) return Promise.resolve(null);
  if (!buffers[url]) {
    buffers[url] = fetch(url).then(r => r.arrayBuffer()).then(b => actx.decodeAudioData(b)).catch(() => null);
  }
  return Promise.resolve(buffers[url]);
}
function initAudio() {
  if (actx) return;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  actx = new AC();
  musicGain = actx.createGain(); sfxGain = actx.createGain(); speechGain = actx.createGain();
  musicGain.gain.value = MUSIC_VOLUME; sfxGain.gain.value = SFX_VOLUME; speechGain.gain.value = 1;
  musicGain.connect(actx.destination); sfxGain.connect(actx.destination); speechGain.connect(actx.destination);
  for (const u of ["sfx/laser.wav", "sfx/fail.wav"]) loadBuffer(u);
  loadBuffer("sfx/music_loop.wav").then(buf => {
    if (!buf) return;
    musicSrc = actx.createBufferSource();
    musicSrc.buffer = buf; musicSrc.loop = true;
    musicSrc.connect(musicGain); musicSrc.start();
  });
}
function play(url, gain) {
  if (!actx) return;
  loadBuffer(url).then(buf => {
    if (!buf) return;
    const s = actx.createBufferSource();
    s.buffer = buf; s.connect(gain); s.start();
  });
}
const sfx = name => play("sfx/" + name + ".wav", sfxGain);
function say(name) {
  if (actx) play("audio/" + encodeURIComponent(name) + ".mp3", speechGain);
}
const sayText = t => say(PUNCT_AUDIO[t] || t);
function toggleMute() {
  muted = !muted;
  if (!actx) return;
  musicGain.gain.value = muted ? 0 : MUSIC_VOLUME;
  sfxGain.gain.value = muted ? 0 : SFX_VOLUME;
  speechGain.gain.value = muted ? 0 : 1;
}

// ---------------------------------------------------------------- word pools
function maxLengthForScore(score) {
  return Math.min(maxLen, 3 + Math.floor(score / SCORE_PER_LENGTH));
}
function poolByMaxLength(n) {
  const pool = [];
  for (const [len, words] of Object.entries(dictionary)) if (+len <= n) pool.push(...words);
  return pool;
}
const randChoice = a => a[Math.floor(Math.random() * a.length)];

function pickNormalText(existing, recent, score) {
  const letterChance = Math.max(0.1, 0.5 - (score / 3000) * 0.4);
  const pool = Math.random() >= letterChance ? poolByMaxLength(maxLengthForScore(score)) : NORMAL_POOL;
  let choices = pool.filter(t => !existing.includes(t) && !recent.includes(t));
  if (!choices.length) choices = pool.filter(t => !existing.includes(t));
  if (!choices.length) choices = pool;
  return randChoice(choices);
}

// ---------------------------------------------------------------- game state
let state = "gate";           // gate | menu | playing
let mode = null;              // beginner | normal
let g;                        // per-run state

function resetRun() {
  g = {
    shipX: SCREEN_W / 2, shipY: MAIN_H - 60, shipAngle: 0,
    words: [], lasers: [], spawnTimer: 0, elapsed: 0, score: 0, lives: LIVES_START,
    target: null, gameOver: false, beginnerTimer: 0, wrongTimer: 0,
    recentWords: [], recentNormal: [],
  };
}
resetRun();

function setHeight(h) { canvas.height = h; fitCanvas(); }
function fitCanvas() {
  const scale = Math.min(window.innerWidth / SCREEN_W, window.innerHeight / canvas.height);
  canvas.style.width = Math.floor(SCREEN_W * scale) + "px";
  canvas.style.height = Math.floor(canvas.height * scale) + "px";
}
window.addEventListener("resize", fitCanvas);

function startBeginner() { setHeight(MAIN_H + KEYBOARD_H); resetRun(); mode = "beginner"; state = "playing"; spawnBeginner(); }
function startNormal() { setHeight(MAIN_H); resetRun(); mode = "normal"; state = "playing"; }
function goMenu() { setHeight(MAIN_H); state = "menu"; mode = null; }

const diffT = () => Math.min(1, g.elapsed / RAMP_TIME);
const fallSpeed = () => FALL_START + (FALL_MAX - FALL_START) * diffT();
const spawnInterval = () => SPAWN_START + (SPAWN_MIN - SPAWN_START) * diffT();
const maxWords = () => Math.round(MAX_WORDS_START + (MAX_WORDS_END - MAX_WORDS_START) * diffT());

function textWidth(text, size) { ctx.font = size + "px " + FONT; return ctx.measureText(text).width; }

function spawnNormal() {
  const text = pickNormalText(g.words.map(w => w.text), g.recentNormal, g.score);
  g.recentNormal.push(text);
  while (g.recentNormal.length > normalRecentMax) g.recentNormal.shift();
  const margin = 40, half = textWidth(text, 32) / 2;
  const lo = Math.round(margin + half), hi = Math.round(SCREEN_W - margin - half);
  const x = lo < hi ? lo + Math.floor(Math.random() * (hi - lo + 1)) : SCREEN_W / 2;
  g.words.push({ text, x, y: TOP_BAR_H - 20, speed: fallSpeed(), typed: 0 });
}
function spawnBeginner() {
  const pool = poolByMaxLength(maxLengthForScore(g.score));
  const text = randChoice(pool.filter(w => !g.recentWords.includes(w)).length ? pool.filter(w => !g.recentWords.includes(w)) : pool);
  const word = { text, x: SCREEN_W / 2, y: BEGINNER_WORD_Y, speed: 0, typed: 0 };
  g.words = [word]; g.target = word;
  say(text);
  g.recentWords.push(text);
  while (g.recentWords.length > RECENT_WORDS) g.recentWords.shift();
}

function charTargetPos(word, i) {
  i = Math.max(0, Math.min(i, word.text.length - 1));
  const cw = textWidth("M", 48);
  return [word.x - cw * word.text.length / 2 + cw * i + cw / 2, word.y + 28];
}
function fireLaser(word) {
  const [tx, ty] = mode === "beginner" ? charTargetPos(word, word.typed - 1) : [word.x, word.y];
  const dx = tx - g.shipX, dy = ty - g.shipY, d = Math.hypot(dx, dy) || 1;
  g.lasers.push({ x: g.shipX, y: g.shipY, vx: dx / d * LASER_SPEED, vy: dy / d * LASER_SPEED, alive: true });
  g.shipAngle = Math.atan2(dx, -dy);
  sfx("laser");
}
function destroyWord(word) {
  g.words = g.words.filter(w => w !== word);
  g.score += word.text.length * 10;
}
function wrongKey() { g.wrongTimer = WRONG_FLASH; sfx("fail"); }

function handleChar(ch) {
  if (g.target && g.words.includes(g.target)) {
    if (g.target.text[g.target.typed] === ch) {
      g.target.typed++;
      fireLaser(g.target);
      if (g.target.typed >= g.target.text.length) {
        const done = g.target;
        destroyWord(done); g.target = null;
        if (mode === "beginner") g.beginnerTimer = BEGINNER_DELAY;
        else sayText(done.text);
      }
    } else wrongKey();
    return;
  }
  const cands = g.words.filter(w => w.text[w.typed] === ch).sort((a, b) => b.y - a.y);
  if (!cands.length) return;
  const w = cands[0];
  w.typed++; g.target = w; fireLaser(w);
  if (w.typed >= w.text.length) { destroyWord(w); g.target = null; sayText(w.text); }
}

function update(dt) {
  if (state !== "playing" || g.gameOver) return;
  g.elapsed += dt;
  if (g.wrongTimer > 0) g.wrongTimer = Math.max(0, g.wrongTimer - dt);
  if (mode === "beginner" && g.beginnerTimer > 0) {
    g.beginnerTimer -= dt;
    if (g.beginnerTimer <= 0) spawnBeginner();
  }
  if (mode === "normal") {
    g.spawnTimer += dt;
    if (g.words.length < maxWords() && g.spawnTimer >= spawnInterval()) { g.spawnTimer = 0; spawnNormal(); }
  }
  for (const w of g.words) w.y += w.speed * dt;
  const h = canvas.height;
  for (const l of g.lasers) {
    l.x += l.vx * dt; l.y += l.vy * dt;
    if (l.x < -50 || l.x > SCREEN_W + 50 || l.y < -50 || l.y > MAIN_H + 50) l.alive = false;
  }
  g.lasers = g.lasers.filter(l => l.alive);
  if (mode === "normal") {
    for (const w of g.words.filter(w => w.y >= MAIN_H - 40)) {
      g.words = g.words.filter(x => x !== w);
      if (w === g.target) g.target = null;
      g.lives--; sfx("fail");
      if (g.lives <= 0) g.gameOver = true;
    }
  }
}

// ---------------------------------------------------------------- drawing
function text(str, x, y, size, color, align = "left", bold = false) {
  ctx.font = (bold ? "bold " : "") + size + "px " + FONT;
  ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = "middle";
  ctx.fillText(str, x, y);
}
function draw() {
  ctx.fillStyle = "#05050f"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (state === "gate") return drawGate();
  if (state === "menu") return drawMenu();
  drawPlay(); drawTopBar();
  if (mode === "beginner") drawKeyboard();
}
function drawGate() {
  text("Kinder Type", SCREEN_W / 2, MAIN_H / 2 - 60, 56, TARGET, "center");
  const ready = Object.keys(dictionary).length > 0;
  text(ready ? "Press any key to start" : "Loading…", SCREEN_W / 2, MAIN_H / 2 + 20, 30, TEXT, "center");
}
function menuOption(num, label, y) {
  const badge = 46, gap = 16;
  const tw = textWidth(label, 30), startX = (SCREEN_W - (badge + gap + tw)) / 2;
  ctx.strokeStyle = TARGET; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.roundRect(startX, y - badge / 2, badge, badge, 8); ctx.stroke();
  text(num, startX + badge / 2, y, 30, TARGET, "center", true);
  text(label, startX + badge + gap, y, 30, TEXT);
}
function drawMenu() {
  text("Kinder Type", SCREEN_W / 2, MAIN_H / 2 - 120, 56, TARGET, "center");
  menuOption("1", "Beginner Mode", MAIN_H / 2 - 10);
  menuOption("2", "Normal Mode", MAIN_H / 2 + 60);
  text(muted ? "M to unmute" : "M to mute", SCREEN_W / 2, MAIN_H / 2 + 140, 24, TEXT, "center");
}
function drawShip() {
  const R = SHIP_RADIUS, pts = [[0, -R], [-R * .7, R * .8], [-R * .25, R * .35], [R * .25, R * .35], [R * .7, R * .8]];
  const c = Math.cos(g.shipAngle), s = Math.sin(g.shipAngle);
  ctx.strokeStyle = "#c8dcff"; ctx.lineWidth = 2; ctx.beginPath();
  pts.forEach(([x, y], i) => {
    const px = g.shipX + x * c - y * s, py = g.shipY + x * s + y * c;
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  });
  ctx.closePath(); ctx.stroke();
}
function drawPlay() {
  const size = mode === "beginner" ? 48 : 32;
  for (const w of g.words) {
    const isTarget = w === g.target, shaking = isTarget && g.wrongTimer > 0;
    const typed = w.text.slice(0, w.typed), rest = w.text.slice(w.typed);
    const tw = textWidth(typed, size), rw = textWidth(rest, size);
    const shake = shaking ? SHAKE_PX * Math.sin(g.wrongTimer * SHAKE_HZ * 2 * Math.PI) : 0;
    const x = w.x - (tw + rw) / 2 + shake, y = w.y + size * 0.6;
    text(typed, x, y, size, LASER);
    text(rest, x + tw, y, size, shaking ? LASER : (isTarget ? TARGET : TEXT));
  }
  ctx.strokeStyle = LASER; ctx.lineWidth = 3;
  for (const l of g.lasers) {
    const d = Math.hypot(l.vx, l.vy) || 1;
    ctx.beginPath(); ctx.moveTo(l.x - l.vx / d * LASER_BOLT_LEN, l.y - l.vy / d * LASER_BOLT_LEN);
    ctx.lineTo(l.x, l.y); ctx.stroke();
  }
  drawShip();
  if (g.gameOver) {
    const cy = TOP_BAR_H + (MAIN_H - TOP_BAR_H) / 2;
    text("GAME OVER", SCREEN_W / 2, cy - 20, 64, OVER, "center");
    text("Press any key to return to the menu", SCREEN_W / 2, cy + 40, 24, TEXT, "center");
  }
}
function drawTopBar() {
  ctx.fillStyle = "#0a0a19"; ctx.fillRect(0, 0, SCREEN_W, TOP_BAR_H);
  ctx.fillStyle = "#3c3c5a"; ctx.fillRect(0, TOP_BAR_H, SCREEN_W, 2);
  let left = 16;
  if (logo.complete && logo.naturalWidth) {
    const w = 28 * logo.naturalWidth / logo.naturalHeight;
    ctx.drawImage(logo, left, (TOP_BAR_H - 28) / 2, w, 28); left += w + 10;
  }
  text("Score: " + g.score, left, TOP_BAR_H / 2, 24, HUD);
  if (mode === "normal") text("Lives: " + g.lives, SCREEN_W - 16, TOP_BAR_H / 2, 24, HUD, "right");
}
function drawKeyboard() {
  ctx.fillStyle = "#000"; ctx.fillRect(0, MAIN_H, SCREEN_W, KEYBOARD_H);
  const next = g.target ? g.target.text[g.target.typed] : null;
  const blinkOn = Math.floor(performance.now() / BLINK_PERIOD_MS) % 2 === 0;
  const pitch = 50, keyH = 38, gap = 4, startX = (SCREEN_W - (ROW_UNITS * pitch - gap)) / 2;
  KEYBOARD_ROWS.forEach((row, ri) => {
    const y = MAIN_H + 14 + ri * (keyH + gap);
    let x = startX;
    for (const [label, units] of row) {
      const kw = units * pitch - gap;
      const isLetter = label.length === 1 && /[A-Z]/.test(label);
      let out, let_;
      if (isLetter && label.toLowerCase() === next) out = let_ = blinkOn ? BLINK : WHITE;
      else if (isLetter) out = let_ = WHITE;
      else { out = INERT_OUT; let_ = INERT_LET; }
      ctx.strokeStyle = out; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.roundRect(x, y, kw, keyH, 5); ctx.stroke();
      text(label, x + kw / 2, y + keyH / 2, 18, let_, "center");
      x += kw + gap;
    }
  });
}

// ---------------------------------------------------------------- input / loop
window.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (state === "gate") {
    if (!Object.keys(dictionary).length) return;
    e.preventDefault(); initAudio(); state = "menu"; say("welcome"); return;
  }
  if (e.key === "Escape") { if (state === "playing") goMenu(); return; }
  const k = e.key.length === 1 ? e.key.toLowerCase() : "";
  if (state === "menu") {
    if (k === "1") startBeginner(); else if (k === "2") startNormal(); else if (k === "m") toggleMute();
    e.preventDefault(); return;
  }
  e.preventDefault();
  if (g.gameOver) { goMenu(); return; }
  if (k && (/^[a-z]$/.test(k) || PUNCT.includes(k))) handleChar(k);
});

let last = performance.now();
function frame(now) {
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  update(dt); draw();
  requestAnimationFrame(frame);
}

fetch("words.json").then(r => r.json()).then(d => {
  dictionary = d;
  maxLen = Math.max(...Object.keys(d).map(Number));
  allWords = Object.values(d).flat();
  normalRecentMax = Math.max(15, Math.round(allWords.length * 0.05));
});
fitCanvas();
requestAnimationFrame(frame);
