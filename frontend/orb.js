// Visualizador central estilo JARVIS: esfera de partículas ámbar con anillos
// orbitales, líneas, núcleo brillante y arcos HUD. Todo dibujado con canvas 2D,
// sin dependencias.
//
// Reacciona a:
//   - el estado del asistente (idle / listening / thinking / speaking)
//   - el nivel de audio real (micrófono y voz de JARVIS) vía setAudio()
//   - el ratón (la esfera crece, gira más rápido y las partículas se apartan)

const C = {
  core: [255, 150, 60],
  point: [255, 185, 115],
  hot: [255, 235, 200],   // color a alta energía
  line: [255, 140, 50],
  ring: [255, 170, 90],
  glow: [255, 140, 60],
};

const BASE_ENERGY = {
  idle: 0.12,
  listening: 0.45,
  thinking: 0.6,
  speaking: 0.9,
};

function mix(a, b, t) {
  return [
    Math.round(a[0] + (b[0] - a[0]) * t),
    Math.round(a[1] + (b[1] - a[1]) * t),
    Math.round(a[2] + (b[2] - a[2]) * t),
  ];
}

function rgba(c, a) {
  return `rgba(${c[0]},${c[1]},${c[2]},${a})`;
}

export class Orb {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);

    this.points = [];   // esfera interior
    this.halo = [];     // esfera exterior, más tenue
    this.rings = this._makeRings();

    this.angle = 0;
    this.state = "idle";
    this.energy = 0;    // energía visual suavizada
    this.audio = 0;     // nivel de audio en crudo (0..1)
    this.audioS = 0;    // nivel de audio suavizado
    this.hover = 0;
    this.hoverTarget = 0;
    this.pulse = 0;
    this.listen = 0;        // brillo extra cuando escucha
    this.listenTarget = 0;
    this.onClick = null;    // el holograma actúa de botón
    this.mouse = { x: 0, y: 0, inside: false };

    this._resize();
    window.addEventListener("resize", () => this._resize());
    this._bindMouse();
    this._seed();
    requestAnimationFrame((t) => this._loop(t));
  }

  _resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.canvas.width = w * this.dpr;
    this.canvas.height = h * this.dpr;
    this.canvas.style.width = w + "px";
    this.canvas.style.height = h + "px";
    this.cx = w / 2;
    this.cy = h / 2;
    this.radius = Math.min(w, h) * 0.24;
    this.persp = 340;
  }

  _bindMouse() {
    window.addEventListener("mousemove", (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
      const d = Math.hypot(e.clientX - this.cx, e.clientY - this.cy);
      this.mouse.inside = d < this.radius * 1.9;
      this.hoverTarget = this.mouse.inside ? 1 : 0;
    });
    window.addEventListener("mouseleave", () => {
      this.mouse.inside = false;
      this.hoverTarget = 0;
    });
    this.canvas.addEventListener("click", () => {
      this.pulse = 1;
      if (typeof this.onClick === "function") this.onClick();
    });
    window.addEventListener("touchmove", (e) => {
      const t = e.touches[0];
      if (!t) return;
      this.mouse.x = t.clientX;
      this.mouse.y = t.clientY;
      this.mouse.inside =
        Math.hypot(t.clientX - this.cx, t.clientY - this.cy) < this.radius * 1.9;
      this.hoverTarget = this.mouse.inside ? 1 : 0;
    }, { passive: true });
  }

  _seed() {
    const core = 1000;
    for (let i = 0; i < core; i++) {
      const y = 1 - (i / (core - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = i * Math.PI * (3 - Math.sqrt(5));
      this.points.push({ x: Math.cos(theta) * r, y, z: Math.sin(theta) * r });
    }
    const halo = 340;
    for (let i = 0; i < halo; i++) {
      const y = 1 - (i / (halo - 1)) * 2;
      const r = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = i * Math.PI * (3 - Math.sqrt(5));
      this.halo.push({
        x: Math.cos(theta) * r, y, z: Math.sin(theta) * r,
        f: 1.28 + Math.random() * 0.5,   // factor de radio
        s: 0.4 + Math.random() * 0.6,    // brillo
      });
    }
  }

  _makeRings() {
    const rings = [
      { r: 1.26, tiltX: 0.28, tiltZ: 0.0, spin: 0.55, seg: 96, w: 1.0, a: 0.55, dash: null },
      { r: 1.46, tiltX: -0.55, tiltZ: 0.42, spin: -0.4, seg: 96, w: 0.8, a: 0.40, dash: [2, 7] },
      { r: 1.64, tiltX: 1.15, tiltZ: -0.3, spin: 0.3, seg: 120, w: 0.7, a: 0.28, dash: null },
      { r: 1.16, tiltX: 0.05, tiltZ: 0.9, spin: -0.85, seg: 80, w: 1.2, a: 0.5, dash: [12, 16] },
    ];
    for (const ring of rings) {
      const pts = [];
      const cx = Math.cos(ring.tiltX), sx = Math.sin(ring.tiltX);
      const cz = Math.cos(ring.tiltZ), sz = Math.sin(ring.tiltZ);
      for (let i = 0; i < ring.seg; i++) {
        const a = (i / ring.seg) * Math.PI * 2;
        let x = Math.cos(a), y = Math.sin(a), z = 0;
        const y2 = y * cx - z * sx, z2 = y * sx + z * cx;
        const x2 = x * cz - y2 * sz;
        pts.push({ x: x2, y: x * sz + y2 * cz, z: z2 });
      }
      ring.pts = pts;
    }
    return rings;
  }

  setState(state) {
    this.state = state in BASE_ENERGY ? state : "idle";
    this.listenTarget = state === "listening" ? 1 : 0;
  }

  // Compatibilidad con el código anterior.
  speaking(on) { this.setState(on ? "speaking" : "idle"); }

  setAudio(level) {
    this.audio = Math.max(0, Math.min(1, level || 0));
  }

  _loop(t) {
    const ctx = this.ctx;
    const base = BASE_ENERGY[this.state] ?? 0.12;
    this.audioS += (this.audio - this.audioS) * 0.25;
    this.energy += (base + this.audioS * 0.7 - this.energy) * 0.08;
    this.hover += (this.hoverTarget - this.hover) * 0.08;
    this.listen += (this.listenTarget - this.listen) * 0.1;
    this.pulse *= 0.92;

    this.angle += 0.0022 + this.energy * 0.006 + this.hover * 0.010 + this.listen * 0.006;

    const wobble = 1 + this.energy * 0.10 + this.hover * 0.06
      + this.audioS * 0.14 + this.pulse * 0.12 + this.listen * 0.05
      + Math.sin(t / 500) * 0.012 * (1 + this.energy);

    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    const R = this.radius * wobble;
    const cosA = Math.cos(this.angle), sinA = Math.sin(this.angle);
    const proj = (x, y, z, r) => {
      const X = x * cosA - z * sinA;
      const Z = x * sinA + z * cosA;
      const s = this.persp / (this.persp + Z * r);
      return { sx: this.cx + X * r * s, sy: this.cy + y * r * s, z: Z, s };
    };

    // 1) Halo de fondo.
    const glow = ctx.createRadialGradient(this.cx, this.cy, R * 0.3,
      this.cx, this.cy, R * 2.2);
    glow.addColorStop(0, rgba(C.glow, 0.07 + this.energy * 0.10 + this.hover * 0.08));
    glow.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // 2) Anillos orbitales (brillo según profundidad).
    for (const ring of this.rings) {
      const spin = this.angle * ring.spin * 2 + t * 0.00012 * ring.spin;
      const rr = R * ring.r * (1 + this.energy * 0.06);
      const pts = ring.pts;
      ctx.lineWidth = ring.w;
      if (ring.dash) ctx.setLineDash(ring.dash); else ctx.setLineDash([]);
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        const pa = proj(a.x, a.y, a.z, rr);
        const pb = proj(b.x, b.y, b.z, rr);
        const depth = (1 - (pa.z + pb.z) / 2) / 2;      // 0 atrás .. 1 delante
        const alpha = ring.a * (0.18 + depth * 0.9) * (0.6 + this.energy * 0.7);
        ctx.strokeStyle = rgba(C.ring, alpha);
        ctx.beginPath();
        ctx.moveTo(pa.sx, pa.sy);
        ctx.lineTo(pb.sx, pb.sy);
        ctx.stroke();
      }
      ctx.setLineDash([]);
    }

    // 3) Arcos HUD 2D concéntricos girando alrededor del núcleo.
    this._hudArcs(ctx, R, t);

    // 4) Enlaces entre partículas cercanas.
    const coreProj = this.points.map((p) => proj(p.x, p.y, p.z, R));
    const linkDist = R * 0.17;
    ctx.lineWidth = 0.6;
    for (let i = 0; i < coreProj.length; i += 4) {
      const a = coreProj[i];
      for (let j = i + 1; j < Math.min(i + 13, coreProj.length); j++) {
        const b = coreProj[j];
        const dx = a.sx - b.sx, dy = a.sy - b.sy;
        if (dx * dx + dy * dy < linkDist * linkDist) {
          const alpha = (1 - Math.abs((a.z + b.z) / 2)) * 0.20
            * (0.35 + this.energy + this.hover * 0.6);
          ctx.strokeStyle = rgba(C.line, alpha);
          ctx.beginPath();
          ctx.moveTo(a.sx, a.sy);
          ctx.lineTo(b.sx, b.sy);
          ctx.stroke();
        }
      }
    }

    // 5) Partículas interiores (con repulsión del cursor).
    const repel = R * 0.55;
    const hotT = Math.min(1, this.energy * 0.6 + this.audioS * 0.7);
    const pcol = mix(C.point, C.hot, hotT);
    for (const p of coreProj) {
      const depth = (p.z + 1) / 2;
      let sx = p.sx, sy = p.sy;
      if (this.hover > 0.01) {
        const dx = sx - this.mouse.x, dy = sy - this.mouse.y;
        const dist = Math.hypot(dx, dy);
        if (dist < repel && dist > 0.01) {
          const force = (1 - dist / repel) * this.hover * 26;
          sx += (dx / dist) * force;
          sy += (dy / dist) * force;
        }
      }
      const alpha = 0.22 + depth * 0.62;
      const size = (0.9 + depth * 1.6) * p.s
        * (1 + this.energy * 0.7 + this.hover * 0.35 + this.audioS * 0.6);
      ctx.fillStyle = rgba(pcol, alpha);
      ctx.beginPath();
      ctx.arc(sx, sy, size, 0, Math.PI * 2);
      ctx.fill();
    }

    // 6) Halo de partículas exterior.
    const hcol = mix(C.ring, C.hot, hotT * 0.7);
    for (const p of this.halo) {
      const pp = proj(p.x, p.y, p.z, R * p.f);
      const depth = (pp.z + 1) / 2;
      const alpha = (0.10 + depth * 0.35) * p.s * (0.7 + this.energy * 0.5);
      ctx.fillStyle = rgba(hcol, alpha);
      ctx.beginPath();
      ctx.arc(pp.sx, pp.sy, 0.8 + depth * 1.2, 0, Math.PI * 2);
      ctx.fill();
    }

    // 7) Núcleo brillante.
    const coreGlow = 0.10 + this.energy * 0.16 + this.hover * 0.14
      + this.pulse * 0.3 + this.audioS * 0.2;
    const core = ctx.createRadialGradient(this.cx, this.cy, 0,
      this.cx, this.cy, R * 0.95);
    core.addColorStop(0, rgba(C.core, Math.min(0.85, coreGlow)));
    core.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = core;
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // 8) Onda de pulso al hacer clic.
    if (this.pulse > 0.02) {
      ctx.strokeStyle = rgba(C.core, this.pulse * 0.5);
      ctx.lineWidth = 2 * this.pulse;
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, R * (1.05 + (1 - this.pulse) * 0.9), 0, Math.PI * 2);
      ctx.stroke();
    }

    requestAnimationFrame((tt) => this._loop(tt));
  }

  _hudArcs(ctx, R, t) {
    const rot = t * 0.0004;

    // Anillo vivo mientras escucha: late y gira, señal de que puede oírte.
    if (this.listen > 0.02) {
      const beat = 0.6 + Math.sin(t / 260) * 0.4;
      ctx.save();
      ctx.translate(this.cx, this.cy);
      ctx.rotate(-rot * 4);
      ctx.setLineDash([6, 9]);
      ctx.lineWidth = 2.2;
      ctx.strokeStyle = rgba(C.hot, this.listen * 0.5 * beat);
      ctx.beginPath();
      ctx.arc(0, 0, R * 1.02, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    const groups = [
      { r: 1.08, dash: [40, 22], w: 1.4, a: 0.5, dir: 1 },
      { r: 1.12, dash: [4, 10], w: 1.0, a: 0.35, dir: -1 },
      { r: 1.9, dash: [90, 60], w: 1.2, a: 0.28, dir: 1 },
      { r: 1.95, dash: [3, 14], w: 0.8, a: 0.22, dir: -1 },
    ];
    for (const g of groups) {
      ctx.save();
      ctx.translate(this.cx, this.cy);
      ctx.rotate(rot * g.dir * 3);
      ctx.setLineDash(g.dash);
      ctx.lineWidth = g.w;
      ctx.strokeStyle = rgba(C.ring, g.a * (0.6 + this.energy * 0.6));
      ctx.beginPath();
      ctx.arc(0, 0, R * g.r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }
  }
}
