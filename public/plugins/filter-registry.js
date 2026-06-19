window.MeTuberFilterRegistry = {
  version: "1.0.0",
  plugins: [
    {
      id: "normal",
      name: "Normal",
      category: "Base",
      description: "No visual filter.",
      cssFilter: "none",
      parameters: {
        strength: { type: "range", min: 0.5, max: 4, step: 0.1, default: 1.8, label: "Edge Strength" },
        threshold: { type: "range", min: 0, max: 255, step: 1, default: 35, label: "Edge Threshold" },
        invert: { type: "range", min: 0, max: 1, step: 1, default: 0, label: "Invert" }
      }
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
      parameters: {
        levels: { type: "range", min: 3, max: 16, step: 1, default: 6, label: "Color Levels" },
        saturation: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.45, label: "Saturation" },
        contrast: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Contrast" }
      }
    },
    {
      id: "dream",
      name: "Dream",
      category: "Preset",
      description: "Dream.OS hue-shifted saturation.",
      cssFilter: "hue-rotate(35deg) saturate(1.8) contrast(1.1)",
      parameters: {
        levels: { type: "range", min: 3, max: 20, step: 1, default: 7, label: "Anime Levels" },
        saturation: { type: "range", min: 0.5, max: 3.5, step: 0.1, default: 1.7, label: "Saturation" },
        brightness: { type: "range", min: -40, max: 60, step: 1, default: 12, label: "Brightness" },
        hue: { type: "range", min: -60, max: 60, step: 1, default: 8, label: "Hue Push" }
      }
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
  edgeDetect(imageData, params = {}) {
    const strength = Number(params.strength ?? 1.8);
    const threshold = Number(params.threshold ?? 35);
    const invert = Number(params.invert ?? 0);

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

        let mag = Math.sqrt(gx*gx + gy*gy) * strength;
        mag = mag < threshold ? 0 : Math.min(255, mag);
        if (invert) mag = 255 - mag;

        const o = i * 4;
        out[o] = out[o+1] = out[o+2] = mag;
        out[o+3] = 255;
      }
    }

    imageData.data.set(out);
    return imageData;
  },

  cartoon(imageData, params = {}) {
    const levels = Number(params.levels ?? 6);
    const saturation = Number(params.saturation ?? 1.45);
    const contrast = Number(params.contrast ?? 1.25);
    const step = Math.max(1, 255 / Math.max(2, levels));
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      let r = Math.round(d[i] / step) * step;
      let g = Math.round(d[i+1] / step) * step;
      let b = Math.round(d[i+2] / step) * step;

      const avg = (r + g + b) / 3;
      r = avg + (r - avg) * saturation;
      g = avg + (g - avg) * saturation;
      b = avg + (b - avg) * saturation;

      r = (r - 128) * contrast + 128;
      g = (g - 128) * contrast + 128;
      b = (b - 128) * contrast + 128;

      d[i] = Math.max(0, Math.min(255, r));
      d[i+1] = Math.max(0, Math.min(255, g));
      d[i+2] = Math.max(0, Math.min(255, b));
    }

    return imageData;
  },

  anime(imageData, params = {}) {
    const levels = Number(params.levels ?? 7);
    const saturation = Number(params.saturation ?? 1.7);
    const brightness = Number(params.brightness ?? 12);
    const hue = Number(params.hue ?? 8);
    const step = Math.max(1, 255 / Math.max(2, levels));
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      let r = Math.round(d[i] / step) * step;
      let g = Math.round(d[i+1] / step) * step;
      let b = Math.round(d[i+2] / step) * step;

      const avg = (r + g + b) / 3;
      r = avg + (r - avg) * saturation + brightness + hue;
      g = avg + (g - avg) * saturation + brightness;
      b = avg + (b - avg) * saturation + brightness + hue * 0.5;

      d[i] = Math.max(0, Math.min(255, r));
      d[i+1] = Math.max(0, Math.min(255, g));
      d[i+2] = Math.max(0, Math.min(255, b));
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
    parameters: {
      strength: { type: "range", min: 0.5, max: 4, step: 0.1, default: 1.8, label: "Edge Strength" },
      threshold: { type: "range", min: 0, max: 255, step: 1, default: 35, label: "Edge Threshold" },
      invert: { type: "range", min: 0, max: 1, step: 1, default: 0, label: "Invert" }
    }
  },
  {
    id: "real-cartoon",
    name: "Real Cartoon",
    category: "Favorite",
    description: "Posterized cartoon color processing.",
    cssFilter: "none",
    canvasFilter: "cartoon",
    parameters: {
      levels: { type: "range", min: 3, max: 16, step: 1, default: 6, label: "Color Levels" },
      saturation: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.45, label: "Saturation" },
      contrast: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Contrast" }
    }
  },
  {
    id: "anime-cartoon",
    name: "Anime Cartoon",
    category: "Favorite",
    description: "Anime-style boosted posterized color.",
    cssFilter: "none",
    canvasFilter: "anime",
    parameters: {
      levels: { type: "range", min: 3, max: 20, step: 1, default: 7, label: "Anime Levels" },
      saturation: { type: "range", min: 0.5, max: 3.5, step: 0.1, default: 1.7, label: "Saturation" },
      brightness: { type: "range", min: -40, max: 60, step: 1, default: 12, label: "Brightness" },
      hue: { type: "range", min: -60, max: 60, step: 1, default: 8, label: "Hue Push" }
    }
  }
);


window.MeTuberPreprocess = {
  settings: { enabled: true, smooth: 8, brightness: 8, softness: 0.75 },

  apply(imageData) {
    const settings = this.settings || {};
    if (!settings.enabled) return imageData;

    const w = imageData.width;
    const h = imageData.height;
    const d = imageData.data;
    const src = new Uint8ClampedArray(d);

    const radius = Math.max(0, Math.min(18, Number(settings.smooth || 0)));
    const softness = Math.max(0, Math.min(1, Number(settings.softness ?? 0.75)));
    const brightness = Number(settings.brightness || 0);

    if (radius <= 0 && brightness === 0) return imageData;

    const step = Math.max(1, Math.floor(radius / 3));
    const samples = [
      [0,0],
      [step,0],[-step,0],[0,step],[0,-step],
      [step,step],[-step,step],[step,-step],[-step,-step],
      [radius,0],[-radius,0],[0,radius],[0,-radius]
    ];

    for (let y = radius; y < h - radius; y++) {
      for (let x = radius; x < w - radius; x++) {
        const idx = (y * w + x) * 4;

        let r = 0, g = 0, b = 0, count = 0;
        for (const [ox, oy] of samples) {
          const p = ((y + oy) * w + (x + ox)) * 4;
          r += src[p];
          g += src[p + 1];
          b += src[p + 2];
          count++;
        }

        const avgR = r / count;
        const avgG = g / count;
        const avgB = b / count;

        const originalR = src[idx];
        const originalG = src[idx + 1];
        const originalB = src[idx + 2];

        d[idx] = Math.max(0, Math.min(255, originalR * (1 - softness) + avgR * softness + brightness));
        d[idx + 1] = Math.max(0, Math.min(255, originalG * (1 - softness) + avgG * softness + brightness));
        d[idx + 2] = Math.max(0, Math.min(255, originalB * (1 - softness) + avgB * softness + brightness));
      }
    }

    return imageData;
  }
};ndow.MeTuberFilterRegistry = {
  version: "1.0.0",
  plugins: [
    {
      id: "normal",
      name: "Normal",
      category: "Base",
      description: "No visual filter.",
      cssFilter: "none",
      parameters: {
        strength: { type: "range", min: 0.5, max: 4, step: 0.1, default: 1.8, label: "Edge Strength" },
        threshold: { type: "range", min: 0, max: 255, step: 1, default: 35, label: "Edge Threshold" },
        invert: { type: "range", min: 0, max: 1, step: 1, default: 0, label: "Invert" }
      }
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
      parameters: {
        levels: { type: "range", min: 3, max: 16, step: 1, default: 6, label: "Color Levels" },
        saturation: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.45, label: "Saturation" },
        contrast: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Contrast" }
      }
    },
    {
      id: "dream",
      name: "Dream",
      category: "Preset",
      description: "Dream.OS hue-shifted saturation.",
      cssFilter: "hue-rotate(35deg) saturate(1.8) contrast(1.1)",
      parameters: {
        levels: { type: "range", min: 3, max: 20, step: 1, default: 7, label: "Anime Levels" },
        saturation: { type: "range", min: 0.5, max: 3.5, step: 0.1, default: 1.7, label: "Saturation" },
        brightness: { type: "range", min: -40, max: 60, step: 1, default: 12, label: "Brightness" },
        hue: { type: "range", min: -60, max: 60, step: 1, default: 8, label: "Hue Push" }
      }
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
  edgeDetect(imageData, params = {}) {
    const strength = Number(params.strength ?? 1.8);
    const threshold = Number(params.threshold ?? 35);
    const invert = Number(params.invert ?? 0);

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

        let mag = Math.sqrt(gx*gx + gy*gy) * strength;
        mag = mag < threshold ? 0 : Math.min(255, mag);
        if (invert) mag = 255 - mag;

        const o = i * 4;
        out[o] = out[o+1] = out[o+2] = mag;
        out[o+3] = 255;
      }
    }

    imageData.data.set(out);
    return imageData;
  },

  cartoon(imageData, params = {}) {
    const levels = Number(params.levels ?? 6);
    const saturation = Number(params.saturation ?? 1.45);
    const contrast = Number(params.contrast ?? 1.25);
    const step = Math.max(1, 255 / Math.max(2, levels));
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      let r = Math.round(d[i] / step) * step;
      let g = Math.round(d[i+1] / step) * step;
      let b = Math.round(d[i+2] / step) * step;

      const avg = (r + g + b) / 3;
      r = avg + (r - avg) * saturation;
      g = avg + (g - avg) * saturation;
      b = avg + (b - avg) * saturation;

      r = (r - 128) * contrast + 128;
      g = (g - 128) * contrast + 128;
      b = (b - 128) * contrast + 128;

      d[i] = Math.max(0, Math.min(255, r));
      d[i+1] = Math.max(0, Math.min(255, g));
      d[i+2] = Math.max(0, Math.min(255, b));
    }

    return imageData;
  },

  anime(imageData, params = {}) {
    const levels = Number(params.levels ?? 7);
    const saturation = Number(params.saturation ?? 1.7);
    const brightness = Number(params.brightness ?? 12);
    const hue = Number(params.hue ?? 8);
    const step = Math.max(1, 255 / Math.max(2, levels));
    const d = imageData.data;

    for (let i = 0; i < d.length; i += 4) {
      let r = Math.round(d[i] / step) * step;
      let g = Math.round(d[i+1] / step) * step;
      let b = Math.round(d[i+2] / step) * step;

      const avg = (r + g + b) / 3;
      r = avg + (r - avg) * saturation + brightness + hue;
      g = avg + (g - avg) * saturation + brightness;
      b = avg + (b - avg) * saturation + brightness + hue * 0.5;

      d[i] = Math.max(0, Math.min(255, r));
      d[i+1] = Math.max(0, Math.min(255, g));
      d[i+2] = Math.max(0, Math.min(255, b));
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
    parameters: {
      strength: { type: "range", min: 0.5, max: 4, step: 0.1, default: 1.8, label: "Edge Strength" },
      threshold: { type: "range", min: 0, max: 255, step: 1, default: 35, label: "Edge Threshold" },
      invert: { type: "range", min: 0, max: 1, step: 1, default: 0, label: "Invert" }
    }
  },
  {
    id: "real-cartoon",
    name: "Real Cartoon",
    category: "Favorite",
    description: "Posterized cartoon color processing.",
    cssFilter: "none",
    canvasFilter: "cartoon",
    parameters: {
      levels: { type: "range", min: 3, max: 16, step: 1, default: 6, label: "Color Levels" },
      saturation: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.45, label: "Saturation" },
      contrast: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Contrast" }
    }
  },
  {
    id: "anime-cartoon",
    name: "Anime Cartoon",
    category: "Favorite",
    description: "Anime-style boosted posterized color.",
    cssFilter: "none",
    canvasFilter: "anime",
    parameters: {
      levels: { type: "range", min: 3, max: 20, step: 1, default: 7, label: "Anime Levels" },
      saturation: { type: "range", min: 0.5, max: 3.5, step: 0.1, default: 1.7, label: "Saturation" },
      brightness: { type: "range", min: -40, max: 60, step: 1, default: 12, label: "Brightness" },
      hue: { type: "range", min: -60, max: 60, step: 1, default: 8, label: "Hue Push" }
    }
  }
);


window.MeTuberPreprocess = {
  settings: {
    enabled: true,
    smooth: 2,
    brightness: 8,
    softness: 0.35
  },

  apply(imageData) {
    const settings = this.settings;
    if (!settings.enabled) return imageData;

    const d = imageData.data;
    const copy = new Uint8ClampedArray(d);
    const w = imageData.width;
    const h = imageData.height;
    const radius = Math.max(0, Number(settings.smooth || 0));
    const softness = Math.max(0, Math.min(1, Number(settings.softness ?? 0.35)));
    const brightness = Number(settings.brightness || 0);

    if (radius <= 0 && brightness === 0) return imageData;

    for (let y = radius; y < h - radius; y++) {
      for (let x = radius; x < w - radius; x++) {
        const idx = (y * w + x) * 4;

        let r = 0, g = 0, b = 0, count = 0;
        for (let yy = -radius; yy <= radius; yy++) {
          for (let xx = -radius; xx <= radius; xx++) {
            const p = ((y + yy) * w + (x + xx)) * 4;
            r += copy[p];
            g += copy[p + 1];
            b += copy[p + 2];
            count++;
          }
        }

        const avgR = r / count;
        const avgG = g / count;
        const avgB = b / count;

        d[idx] = Math.max(0, Math.min(255, copy[idx] * (1 - softness) + avgR * softness + brightness));
        d[idx + 1] = Math.max(0, Math.min(255, copy[idx + 1] * (1 - softness) + avgG * softness + brightness));
        d[idx + 2] = Math.max(0, Math.min(255, copy[idx + 2] * (1 - softness) + avgB * softness + brightness));
      }
    }

    return imageData;
  }
};
