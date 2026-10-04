// Orbe de partículas estilo JARVIS, en naranja, sin dependencias (canvas 2D).
// Reacciona al ratón: al acercarlo, la esfera se agranda, gira más rápido y las
// partículas se apartan del cursor. Al hacer clic, emite un pulso.

const ORANGE = {
  core: "255,150,60",
  point: "255,180,110",
  line: "255,140,50",
  glow: "255,140,60",
};

export class Orb {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.dpr = window.devicePixelRatio || 1;
    this.points = [];
    this.angle = 0;
    this.energy = 0;      // sube al hablar
    this.target = 0;
    this.hover = 0;       // sube al acercar el ratón
    this.hoverTarget = 0;
    this.mouse = { x: 0, y: 0, inside: false };
    this.pulse = 0;       // golpe al hacer clic
    this._resize();
    window.addEventListener("resize", () => this._resize());
    this._bindMouse();
    this._seed();
    requestAnimationFrame((t) => this._loop(t));
  }

  _resize() {
    const { innerWidth: w, innerHeight: h } = window;
    this.canvas.width = w * this.dpr;
    this.canvas.height = h * this.dpr;
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
    this.cx = w / 2;
    this.cy = h / 2;
    this.radius = Math.min(w, h) * 0.28;
  }

  _bindMouse() {
    window.addEventListener("mousemove", (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
      const d = Math.hypot(e.clientX - this.cx, e.clientY - this.cy);
      // Zona de influencia: un poco mayor que el orbe.
      this.mouse.inside = d < this.radius * 1.7;
      this.hoverTarget = this.mouse.inside ? 1 : 0;
    });
    window.addEventListener("mouseleave", () => {
      this.mouse.inside = false;
      this.hoverTarget = 0;
    });
    this.canvas.addEventListener("click", () => { this.pulse = 1; });
    // En pantallas táctiles, el toque también interactúa.
    window.addEventListener("touchmove", (e) => {
      const t = e.touches[0];
      if (!t) return;
      this.mouse.x = t.clientX;
      this.mouse.y = t.clientY;
      this.mouse.inside = Math.hypot(t.clientX - this.cx, t.clientY - this.cy) < this.radius * 1.7;
      this.hoverTarget = this.mouse.inside ? 1 : 0;
    }, { passive: true });
  }

  _seed() {
    const n = 1400;
    for (let i = 0; i < n; i++) {
      // Distribución esférica uniforme (Fibonacci).
      const y = 1 - (i / (n - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const theta = i * Math.PI * (3 - Math.sqrt(5));
      this.points.push({ x: Math.cos(theta) * r, y, z: Math.sin(theta) * r });
    }
  }

  speaking(on) { this.target = on ? 1 : 0; }

  _loop(t) {
    const ctx = this.ctx;
    this.energy += (this.target - this.energy) * 0.06;
    this.hover += (this.hoverTarget - this.hover) * 0.08;
    this.pulse *= 0.92;

    // El ratón acelera la rotación y agranda la esfera.
    this.angle += 0.0025 + this.energy * 0.004 + this.hover * 0.010;

    const wobble = 1 + this.energy * 0.10 + this.hover * 0.06
      + Math.sin(t / 400) * 0.01 * (1 + this.energy) + this.pulse * 0.12;
    const cosA = Math.cos(this.angle), sinA = Math.sin(this.angle);

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    const repel = this.radius * 0.5;   // radio de repulsión del cursor
    const projected = this.points.map((p) => {
      // Rotación sobre el eje Y.
      const x = p.x * cosA - p.z * sinA;
      const z = p.x * sinA + p.z * cosA;
      const scale = 300 / (300 + z * this.radius);
      let sx = this.cx + x * this.radius * wobble * scale;
      let sy = this.cy + p.y * this.radius * wobble * scale;

      // Repulsión: las partículas se apartan del cursor (solo si está cerca).
      if (this.hover > 0.01) {
        const dx = sx - this.mouse.x, dy = sy - this.mouse.y;
        const dist = Math.hypot(dx, dy);
        if (dist < repel && dist > 0.01) {
          const force = (1 - dist / repel) * this.hover * 26;
          sx += (dx / dist) * force;
          sy += (dy / dist) * force;
        }
      }
      return { sx, sy, z, scale };
    });

    // Líneas entre puntos cercanos.
    const linkDist = this.radius * 0.18;
    ctx.lineWidth = 0.6;
    for (let i = 0; i < projected.length; i += 3) {
      const a = projected[i];
      for (let j = i + 1; j < Math.min(i + 14, projected.length); j++) {
        const b = projected[j];
        const dx = a.sx - b.sx, dy = a.sy - b.sy;
        if (dx * dx + dy * dy < linkDist * linkDist) {
          const alpha = (1 - Math.abs(a.z)) * 0.20 * (0.4 + this.energy + this.hover * 0.6);
          ctx.strokeStyle = `rgba(${ORANGE.line},${alpha})`;
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          ctx.lineTo(b.sx, b.sy);
          ctx.stroke();
        }
      }
    }

    // Puntos.
    for (const p of projected) {
      const depth = (p.z + 1) / 2;             // 0 atrás .. 1 delante
      const alpha = 0.25 + depth * 0.6;
      const size = (1 + depth * 1.6) * p.scale * (1 + this.energy * 0.6 + this.hover * 0.35);
      ctx.fillStyle = `rgba(${ORANGE.point},${alpha})`;
      ctx.beginPath();
      ctx.arc(p.sx, p.sy, size, 0, Math.PI * 2);
      ctx.fill();
    }

    // Núcleo brillante en el centro (más intenso al acercar el ratón).
    const coreGlow = 0.10 + this.energy * 0.16 + this.hover * 0.14 + this.pulse * 0.3;
    const core = ctx.createRadialGradient(this.cx, this.cy, 0,
      this.cx, this.cy, this.radius * 0.9);
    core.addColorStop(0, `rgba(${ORANGE.core},${coreGlow})`);
    core.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = core;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Halo exterior.
    const glow = ctx.createRadialGradient(this.cx, this.cy, this.radius * 0.4,
      this.cx, this.cy, this.radius * 1.8);
    glow.addColorStop(0, `rgba(${ORANGE.glow},${0.06 + this.energy * 0.10 + this.hover * 0.10})`);
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    requestAnimationFrame((tt) => this._loop(tt));
  }
}
