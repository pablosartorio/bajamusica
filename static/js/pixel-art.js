/* ============================================================
   Sonido · Pixel-art engine
   window.PIXEL.cover(seed)         → data-URI de una criatura única
   window.PIXEL.mountCassette(cv)   → cinta animada con carretes
   window.PIXEL.mountReel(cv)       → carrete solo (panel de descarga)
   ============================================================ */
(function () {
  function hash(str) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function lighten(hex, amt) {
    const n = parseInt(hex.slice(1), 16);
    let r = n >> 16, g = (n >> 8) & 255, b = n & 255;
    return '#' + [r, g, b].map(c => Math.round(c + (255 - c) * amt).toString(16).padStart(2, '0')).join('');
  }

  const BODIES = ['#ef6f3c','#2aa583','#f4b73d','#ee79a6','#4f9fe0','#74c14f','#a87fe0','#e85d5d','#36c0c8','#f0944e'];
  const BGS    = ['#241d15','#1c2620','#261c22','#1b2330','#2a2417','#1d2426'];

  function cover(seed) {
    const rng = mulberry32(hash(String(seed)));
    const GW = 8, GH = 8, half = GW / 2;
    const body = BODIES[Math.floor(rng() * BODIES.length)];
    const bg   = BGS[Math.floor(rng() * BGS.length)];
    const hi   = lighten(body, 0.42);
    const eye  = '#15110b';
    const grid = [];
    let filled = 0;
    for (let y = 0; y < GH; y++) {
      grid[y] = [];
      for (let x = 0; x < half; x++) {
        const edge = (y === 0 || y === GH - 1) ? 0.32 : 0.55;
        const on = rng() < edge;
        grid[y][x] = on;
        if (on) filled++;
      }
    }
    if (filled < 7) { grid[3][half-1]=grid[4][half-1]=grid[3][half-2]=grid[4][half-2]=true; }
    const cv = document.createElement('canvas');
    cv.width = GW; cv.height = GH;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, GW, GH);
    for (let y = 0; y < GH; y++) {
      for (let x = 0; x < half; x++) {
        if (!grid[y][x]) continue;
        ctx.fillStyle = y === 0 ? hi : body;
        ctx.fillRect(x, y, 1, 1);
        ctx.fillRect(GW - 1 - x, y, 1, 1);
      }
    }
    const eyeRow = grid[2].some(Boolean) ? 2 : (grid[3].some(Boolean) ? 3 : -1);
    if (eyeRow >= 0) {
      let col = -1;
      for (let x = half - 1; x >= 0; x--) { if (grid[eyeRow][x]) { col = x; break; } }
      if (col >= 0) {
        ctx.fillStyle = eye;
        ctx.fillRect(col, eyeRow, 1, 1);
        ctx.fillRect(GW - 1 - col, eyeRow, 1, 1);
      }
    }
    return cv.toDataURL();
  }

  function disc(ctx, cx, cy, r) {
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
  }
  function drawReel(ctx, cx, cy, r, a) {
    ctx.fillStyle = '#6e4a28'; disc(ctx, cx, cy, r);
    ctx.fillStyle = '#caa46a'; disc(ctx, cx, cy, r * 0.5);
    ctx.strokeStyle = '#15110b'; ctx.lineWidth = 1.3; ctx.lineCap = 'round';
    for (let i = 0; i < 3; i++) {
      const ang = a + i * 2.0944;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(ang) * 1.4, cy + Math.sin(ang) * 1.4);
      ctx.lineTo(cx + Math.cos(ang) * (r - 0.6), cy + Math.sin(ang) * (r - 0.6));
      ctx.stroke();
    }
    ctx.fillStyle = '#15110b'; disc(ctx, cx, cy, 1);
  }

  function drawCassette(ctx, W, H, t) {
    ctx.clearRect(0, 0, W, H);
    const sx = W / 96, sy = H / 60;
    ctx.save(); ctx.scale(sx, sy);
    ctx.fillStyle = '#15110b'; ctx.fillRect(0, 0, 96, 60);
    ctx.fillStyle = '#f4ead2'; ctx.fillRect(2, 2, 92, 56);
    ctx.fillStyle = '#15110b';
    [[5,5],[90,5],[5,54],[90,54]].forEach(([x,y]) => ctx.fillRect(x, y, 1, 1));
    ctx.fillStyle = '#15110b'; ctx.fillRect(8, 7, 80, 15);
    ctx.fillStyle = '#efd29a'; ctx.fillRect(9, 8, 78, 13);
    ctx.fillStyle = '#e0532a'; ctx.fillRect(9, 8, 78, 3);
    ctx.fillStyle = '#c08a3a';
    ctx.fillRect(13, 14, 70, 1); ctx.fillRect(13, 17, 56, 1);
    ctx.fillStyle = '#15110b'; ctx.fillRect(14, 26, 68, 24);
    ctx.fillStyle = '#241c14'; ctx.fillRect(15, 27, 66, 22);
    ctx.fillStyle = '#6e4a28'; ctx.fillRect(34, 30, 28, 2);
    const a = t * 2.2;
    drawReel(ctx, 34, 38, 8, a);
    drawReel(ctx, 62, 38, 8, a);
    ctx.fillStyle = '#15110b';
    ctx.fillRect(28,52,7,4); ctx.fillRect(45,53,6,3); ctx.fillRect(61,52,7,4);
    ctx.restore();
  }

  function drawSoloReel(ctx, W, H, t) {
    ctx.clearRect(0, 0, W, H);
    const s = Math.min(W, H) / 24;
    ctx.save(); ctx.scale(s, s);
    drawReel(ctx, 12, 12, 10, t * 2.6);
    ctx.restore();
  }

  const tickers = [];
  function loop(ts) {
    const sec = ts / 1000;
    for (const fn of tickers) fn(sec);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);

  function mountCassette(cv) {
    if (!cv) return;
    const ctx = cv.getContext('2d');
    tickers.push((t) => drawCassette(ctx, cv.width, cv.height, t));
  }
  function mountReel(cv) {
    if (!cv) return;
    const ctx = cv.getContext('2d');
    tickers.push((t) => drawSoloReel(ctx, cv.width, cv.height, t));
  }

  window.PIXEL = { cover, mountCassette, mountReel };
})();
