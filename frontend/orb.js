// Orbe de partículas estilo JARVIS, sin dependencias (canvas 2D).
// Una esfera hueca de puntos con líneas entre vecinos cercanos, que se hincha
// y brilla cuando JARVIS habla.

export class Orb {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.dpr = window.devicePixelRatio || 1;
    this.points = [];
    this.angle = 0;
    this.energy = 0;      // 0..1, sube al hablar
    this.target = 0;
    this._resize();
    window.addEventListener("resize", () => this._resize());
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
    this.angle += 0.0025 + this.energy * 0.004;

    const wobble = 1 + this.energy * 0.10 + Math.sin(t / 400) * 0.01 * (1 + this.energy);
    const cosA = Math.cos(this.angle), sinA = Math.sin(this.angle);

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    const projected = this.points.map((p) => {
      // Rotación sobre el eje Y.
      const x = p.x * cosA - p.z * sinA;
      const z = p.x * sinA + p.z * cosA;
      const scale = 300 / (300 + z * this.radius);
      return {
        sx: this.cx + x * this.radius * wobble * scale,
        sy: this.cy + p.y * this.radius * wobble * scale,
        z, scale,
      };
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
          const alpha = (1 - Math.abs(a.z)) * 0.18 * (0.4 + this.energy);
          ctx.strokeStyle = `rgba(79,216,255,${alpha})`;
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
      const size = (1 + depth * 1.6) * p.scale * (1 + this.energy * 0.6);
      ctx.fillStyle = `rgba(120,225,255,${alpha})`;
      ctx.beginPath();
      ctx.arc(p.sx, p.sy, size, 0, Math.PI * 2);
      ctx.fill();
    }

    // Halo.
    const glow = ctx.createRadialGradient(this.cx, this.cy, this.radius * 0.4,
      this.cx, this.cy, this.radius * 1.7);
    glow.addColorStop(0, `rgba(79,216,255,${0.06 + this.energy * 0.10})`);
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    requestAnimationFrame((tt) => this._loop(tt));
  }
}
