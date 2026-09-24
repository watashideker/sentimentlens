(() => {
  if (window.__finlensParticles) return; // survive Streamlit reruns: start only once
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  canvas.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:-1;pointer-events:none;';
  document.body.prepend(canvas);
  window.__finlensParticles = true;

  const ctx = canvas.getContext('2d');
  const mouse = { x: -9999, y: -9999 };
  const LINK = 130, PULL = 160;
  let w, h, dpr, pts = [], raf = null;

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = innerWidth; h = innerHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const n = w < 700 ? 25 : Math.min(60, Math.round(w * h / 22000));
    pts = Array.from({ length: n }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3, vy: (Math.random() - 0.5) * 0.3,
      c: Math.random() < 0.5 ? '16,185,129' : '59,130,246',
    }));
  }

  function frame() {
    ctx.clearRect(0, 0, w, h);
    for (const p of pts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
      const dx = p.x - mouse.x, dy = p.y - mouse.y, d2 = dx * dx + dy * dy;
      if (d2 < PULL * PULL && d2 > 1) { // gentle push away from the cursor
        const d = Math.sqrt(d2), f = (1 - d / PULL) * 0.6;
        p.x += (dx / d) * f; p.y += (dy / d) * f;
      }
      ctx.fillStyle = `rgba(${p.c},0.55)`;
      ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, 6.2832); ctx.fill();
    }
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 < LINK * LINK) {
          ctx.strokeStyle = `rgba(${a.c},${0.18 * (1 - Math.sqrt(d2) / LINK)})`;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
    }
    raf = requestAnimationFrame(frame);
  }

  addEventListener('resize', resize);
  addEventListener('mousemove', (e) => { mouse.x = e.clientX; mouse.y = e.clientY; }, { passive: true });
  addEventListener('mouseout', () => { mouse.x = mouse.y = -9999; });
  document.addEventListener('visibilitychange', () => { // stop burning CPU in background tabs
    if (document.hidden) { cancelAnimationFrame(raf); raf = null; } else if (!raf) frame();
  });
  resize(); frame();
})();
