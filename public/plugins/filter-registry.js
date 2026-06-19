window.MeTuberFilterRegistry = {
  version: "1.0.0",
  plugins: [
    {
      id: "normal",
      name: "Normal",
      category: "Base",
      description: "No visual filter.",
      cssFilter: "none",
      parameters: {}
    },
    {
      id: "invert",
      name: "Invert Filter",
      category: "Color",
      description: "Browser adapter for styles/color_filters/invert_filter.py.",
      cssFilter: "invert(1)",
      parameters: {
        intensity: { type: "range", min: 0, max: 1, step: 0.05, default: 1, label: "Intensity" }
      },
      buildFilter(params = {}) {
        const intensity = Number(params.intensity ?? 1);
        return `invert(${Math.max(0, Math.min(1, intensity))})`;
      }
    },
    {
      id: "cartoon",
      name: "Cartoon Effects",
      category: "Artistic",
      description: "Cartoon-style contrast, saturation, and edge-like punch.",
      cssFilter: "contrast(1.45) saturate(1.65) brightness(1.04)",
      parameters: {
        punch: { type: "range", min: 0.8, max: 2, step: 0.05, default: 1.45, label: "Punch" },
        saturation: { type: "range", min: 0.8, max: 2.5, step: 0.05, default: 1.65, label: "Saturation" }
      },
      buildFilter(params = {}) {
        const punch = Number(params.punch ?? 1.45);
        const saturation = Number(params.saturation ?? 1.65);
        return `contrast(${punch}) saturate(${saturation}) brightness(1.04)`;
      }
    },
    {
      id: "color",
      name: "Color Effects",
      category: "Color",
      description: "High color video look.",
      cssFilter: "saturate(1.9) contrast(1.15) hue-rotate(12deg)",
      parameters: {
        saturation: { type: "range", min: 0.5, max: 3, step: 0.05, default: 1.9, label: "Saturation" },
        hue: { type: "range", min: -180, max: 180, step: 1, default: 12, label: "Hue" }
      },
      buildFilter(params = {}) {
        const saturation = Number(params.saturation ?? 1.9);
        const hue = Number(params.hue ?? 12);
        return `saturate(${saturation}) contrast(1.15) hue-rotate(${hue}deg)`;
      }
    },
    {
      id: "sketch",
      name: "Sketch Effects",
      category: "Artistic",
      description: "Black-and-white sketch-style preview.",
      cssFilter: "grayscale(1) contrast(2.2) brightness(1.12)",
      parameters: {
        contrast: { type: "range", min: 1, max: 3, step: 0.05, default: 2.2, label: "Contrast" }
      },
      buildFilter(params = {}) {
        const contrast = Number(params.contrast ?? 2.2);
        return `grayscale(1) contrast(${contrast}) brightness(1.12)`;
      }
    },
    {
      id: "cinema",
      name: "Cinema",
      category: "Preset",
      description: "Cinematic contrast and saturation.",
      cssFilter: "contrast(1.25) saturate(1.25) brightness(.92)",
      parameters: {}
    },
    {
      id: "dream",
      name: "Dream",
      category: "Preset",
      description: "Dream.OS hue-shifted saturation.",
      cssFilter: "hue-rotate(35deg) saturate(1.8) contrast(1.1)",
      parameters: {}
    },
    {
      id: "noir",
      name: "Noir",
      category: "Preset",
      description: "High contrast monochrome.",
      cssFilter: "grayscale(1) contrast(1.4)",
      parameters: {}
    },
    {
      id: "warm",
      name: "Warm",
      category: "Preset",
      description: "Warm sepia color pass.",
      cssFilter: "sepia(.35) saturate(1.3)",
      parameters: {}
    },
    {
      id: "glitch",
      name: "Glitch",
      category: "Preset",
      description: "Aggressive hue and contrast shift.",
      cssFilter: "hue-rotate(120deg) contrast(1.6) saturate(2)",
      parameters: {}
    }
  ],

  validate() {
    const seen = new Set();
    const errors = [];
    for (const plugin of this.plugins) {
      if (!plugin.id) errors.push("missing id");
      if (!plugin.name) errors.push(`${plugin.id || "unknown"} missing name`);
      if (seen.has(plugin.id)) errors.push(`duplicate id ${plugin.id}`);
      seen.add(plugin.id);
      if (!plugin.cssFilter && typeof plugin.buildFilter !== "function") {
        errors.push(`${plugin.id} missing cssFilter/buildFilter`);
      }
    }
    return { ok: errors.length === 0, count: this.plugins.length, errors };
  },

  get(id) {
    return this.plugins.find(plugin => plugin.id === id);
  },

  getFilter(id, params = {}) {
    const plugin = this.get(id);
    if (!plugin) return "none";
    if (typeof plugin.buildFilter === "function") return plugin.buildFilter(params);
    return plugin.cssFilter || "none";
  }
};

// Runtime canvas filters: real frame processing, not CSS-only.
window.MeTuberCanvasFilters = {
  edgeDetect(imageData) {
    const src = imageData.data;
    const w = imageData.width;
    const h = imageData.height;
    const out = new Uint8ClampedArray(src.length);

    const gray = new Uint8ClampedArray(w * h);
    for (let i = 0, p = 0; i < src.length; i += 4, p++) {
      gray[p] = (src[i] * 0.299 + src[i+1] * 0.587 + src[i+2] * 0.114) | 0;
    }

    for (let y = 1; y < h - 1; y++) {
      for (let x = 1; x < w - 1; x++) {
        const i = y * w + x;
        const gx =
          -gray[i-w-1] - 2*gray[i-1] - gray[i+w-1] +
           gray[i-w+1] + 2*gray[i+1] + gray[i+w+1];
        const gy =
          -gray[i-w-1] - 2*gray[i-w] - gray[i-w+1] +
           gray[i+w-1] + 2*gray[i+w] + gray[i+w+1];

        const mag = Math.min(255, Math.sqrt(gx*gx + gy*gy));
        const o = i * 4;
        out[o] = out[o+1] = out[o+2] = mag;
        out[o+3] = 255;
      }
    }

    imageData.data.set(out);
    return imageData;
  },

  cartoon(imageData) {
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      d[i] = Math.floor(d[i] / 48) * 48;
      d[i+1] = Math.floor(d[i+1] / 48) * 48;
      d[i+2] = Math.floor(d[i+2] / 48) * 48;
      d[i] = Math.min(255, d[i] * 1.18);
      d[i+1] = Math.min(255, d[i+1] * 1.12);
      d[i+2] = Math.min(255, d[i+2] * 1.08);
    }

    return imageData;
  },

  anime(imageData) {
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      d[i] = Math.floor(d[i] / 36) * 36;
      d[i+1] = Math.floor(d[i+1] / 36) * 36;
      d[i+2] = Math.floor(d[i+2] / 36) * 36;

      d[i] = Math.min(255, d[i] * 1.28 + 8);
      d[i+1] = Math.min(255, d[i+1] * 1.18 + 6);
      d[i+2] = Math.min(255, d[i+2] * 1.25 + 10);
    }

    return imageData;
  }
};

window.MeTuberFilterRegistry.plugins.unshift(
  {
    id: "edge-detection",
    name: "Edge Detection",
    category: "Favorite",
    description: "Real Sobel edge detection canvas filter.",
    cssFilter: "none",
    canvasFilter: "edgeDetect",
    parameters: {}
  },
  {
    id: "real-cartoon",
    name: "Real Cartoon",
    category: "Favorite",
    description: "Posterized cartoon color processing.",
    cssFilter: "none",
    canvasFilter: "cartoon",
    parameters: {}
  },
  {
    id: "anime-cartoon",
    name: "Anime Cartoon",
    category: "Favorite",
    description: "Anime-style boosted posterized color.",
    cssFilter: "none",
    canvasFilter: "anime",
    parameters: {}
  }
);
