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
      parameters: {
        saturation: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Saturation" },
        contrast: { type: "range", min: 0.5, max: 3, step: 0.1, default: 1.25, label: "Contrast" }
      },
      buildFilter(params = {}) {
        const saturation = Number(params.saturation ?? 1.25);
        const contrast = Number(params.contrast ?? 1.25);
        return `contrast(${contrast}) saturate(${saturation}) brightness(.92)`;
      }
    },
    {
      id: "dream",
      name: "Dream",
      category: "Preset",
      description: "Dream.OS hue-shifted saturation.",
      cssFilter: "hue-rotate(35deg) saturate(1.8) contrast(1.1)",
      parameters: {
        saturation: { type: "range", min: 0.5, max: 3.5, step: 0.1, default: 1.8, label: "Saturation" },
        brightness: { type: "range", min: -40, max: 60, step: 1, default: 0, label: "Brightness" },
        hue: { type: "range", min: -60, max: 60, step: 1, default: 35, label: "Hue Push" }
      },
      buildFilter(params = {}) {
        const saturation = Number(params.saturation ?? 1.8);
        const brightness = Number(params.brightness ?? 0);
        const hue = Number(params.hue ?? 35);
        return `hue-rotate(${hue}deg) saturate(${saturation}) contrast(1.1) brightness(${1 + brightness / 100})`;
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

window.MeTuberCanvasFilters = {
  edgeDetect(imageData, params = {}) {
    const strength = Number(params.strength ?? 1.8);
    const threshold = Number(params.threshold ?? 35);
    const invert = Number(params.invert ?? 0);
    const src = imageData.data;
    const width = imageData.width;
    const height = imageData.height;
    const out = new Uint8ClampedArray(src.length);
    const gray = new Uint8ClampedArray(width * height);

    for (let i = 0, p = 0; i < src.length; i += 4, p++) {
      gray[p] = (src[i] * 0.299 + src[i + 1] * 0.587 + src[i + 2] * 0.114) | 0;
      out[i + 3] = src[i + 3];
    }

    for (let y = 1; y < height - 1; y++) {
      for (let x = 1; x < width - 1; x++) {
        const i = y * width + x;
        const gx =
          -gray[i - width - 1] - 2 * gray[i - 1] - gray[i + width - 1] +
          gray[i - width + 1] + 2 * gray[i + 1] + gray[i + width + 1];
        const gy =
          -gray[i - width - 1] - 2 * gray[i - width] - gray[i - width + 1] +
          gray[i + width - 1] + 2 * gray[i + width] + gray[i + width + 1];

        let magnitude = Math.sqrt(gx * gx + gy * gy) * strength;
        magnitude = magnitude < threshold ? 0 : Math.min(255, magnitude);
        if (invert) magnitude = 255 - magnitude;

        const outIndex = i * 4;
        out[outIndex] = out[outIndex + 1] = out[outIndex + 2] = magnitude;
        out[outIndex + 3] = 255;
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
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      let red = Math.round(data[i] / step) * step;
      let green = Math.round(data[i + 1] / step) * step;
      let blue = Math.round(data[i + 2] / step) * step;
      const average = (red + green + blue) / 3;

      red = average + (red - average) * saturation;
      green = average + (green - average) * saturation;
      blue = average + (blue - average) * saturation;

      data[i] = clampColor((red - 128) * contrast + 128);
      data[i + 1] = clampColor((green - 128) * contrast + 128);
      data[i + 2] = clampColor((blue - 128) * contrast + 128);
    }

    return imageData;
  },

  anime(imageData, params = {}) {
    const levels = Number(params.levels ?? 7);
    const saturation = Number(params.saturation ?? 1.7);
    const brightness = Number(params.brightness ?? 12);
    const hue = Number(params.hue ?? 8);
    const step = Math.max(1, 255 / Math.max(2, levels));
    const data = imageData.data;

    for (let i = 0; i < data.length; i += 4) {
      let red = Math.round(data[i] / step) * step;
      let green = Math.round(data[i + 1] / step) * step;
      let blue = Math.round(data[i + 2] / step) * step;
      const average = (red + green + blue) / 3;

      red = average + (red - average) * saturation + brightness + hue;
      green = average + (green - average) * saturation + brightness;
      blue = average + (blue - average) * saturation + brightness + hue * 0.5;

      data[i] = clampColor(red);
      data[i + 1] = clampColor(green);
      data[i + 2] = clampColor(blue);
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
    smooth: 8,
    brightness: 8,
    softness: 0.75
  },

  apply(imageData) {
    const settings = this.settings || {};
    if (!settings.enabled) return imageData;

    const width = imageData.width;
    const height = imageData.height;
    const data = imageData.data;
    const source = new Uint8ClampedArray(data);
    const radius = Math.max(0, Math.min(18, Number(settings.smooth || 0)));
    const softness = Math.max(0, Math.min(1, Number(settings.softness ?? 0.75)));
    const brightness = Number(settings.brightness || 0);

    if (radius <= 0 && brightness === 0) return imageData;

    const step = Math.max(1, Math.floor(radius / 3));
    const samples = [
      [0, 0],
      [step, 0],
      [-step, 0],
      [0, step],
      [0, -step],
      [step, step],
      [-step, step],
      [step, -step],
      [-step, -step],
      [radius, 0],
      [-radius, 0],
      [0, radius],
      [0, -radius]
    ];

    for (let y = radius; y < height - radius; y++) {
      for (let x = radius; x < width - radius; x++) {
        const index = (y * width + x) * 4;
        let red = 0;
        let green = 0;
        let blue = 0;
        let count = 0;

        for (const [offsetX, offsetY] of samples) {
          const sampleIndex = ((y + offsetY) * width + (x + offsetX)) * 4;
          red += source[sampleIndex];
          green += source[sampleIndex + 1];
          blue += source[sampleIndex + 2];
          count++;
        }

        data[index] = clampColor(source[index] * (1 - softness) + (red / count) * softness + brightness);
        data[index + 1] = clampColor(source[index + 1] * (1 - softness) + (green / count) * softness + brightness);
        data[index + 2] = clampColor(source[index + 2] * (1 - softness) + (blue / count) * softness + brightness);
      }
    }

    return imageData;
  }
};

function clampColor(value) {
  return Math.max(0, Math.min(255, value));
}
