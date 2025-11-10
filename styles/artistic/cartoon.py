import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple
from styles.base import Style


def _ensure_uint8(img: np.ndarray) -> np.ndarray:
    if img.dtype == np.uint8:
        return img
    img_float = img.astype(np.float32)
    img_float = np.clip(img_float, 0, 255)
    return img_float.astype(np.uint8)


def _split_alpha(img: np.ndarray) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    if img.ndim == 3 and img.shape[2] == 4:
        bgr = img[..., :3]
        a = img[..., 3]
        return bgr, a
    return img, None


def _merge_alpha(bgr: np.ndarray, alpha: Optional[np.ndarray]) -> np.ndarray:
    if alpha is None:
        return bgr
    if alpha.dtype != np.uint8:
        alpha = np.clip(alpha, 0, 255).astype(np.uint8)
    return np.dstack([bgr, alpha])


def _is_rgb(img: np.ndarray) -> bool:
    # Heuristic: if image likely loaded via PIL (RGB) vs OpenCV (BGR)
    # We don't convert automatically to avoid color shifts; we just note it.
    return False  # assume BGR since pipeline is OpenCV-native


class CartoonStylePro(Style):
    """
    Unified Cartoon style with multiple quantization & edge pipelines.
    Safe, fast defaults; highly tunable for quality.
    """
    name = "Cartoon"
    category = "Artistic"
    variants = ["Detailed", "Fast", "Advanced", "Anime", "Whole"]
    default_variant = "Detailed"
    PRESET_DEFAULTS: Dict[str, Dict[str, Any]] = {
        "Detailed": {
            "preset": "Detailed",
            "bilateral_passes": 1,
            "bilateral_d": 9,
            "bilateral_sigmaColor": 75,
            "bilateral_sigmaSpace": 75,
            "quant_method": "Uniform",
            "bits": 4,
            "downscale_factor": 0.5,
            "edge_method": "Canny",
            "canny_t1": 80,
            "canny_t2": 180,
            "edge_median_ksize": 7,
            "edge_dilate": 1,
            "edge_erode": 0,
        },
        "Fast": {
            "preset": "Fast",
            "bilateral_passes": 1,
            "quant_method": "Downscale+Uniform",
            "bits": 3,
            "downscale_factor": 0.3,
            "edge_method": "Adaptive",
            "canny_t1": 60,
            "canny_t2": 140,
            "edge_median_ksize": 5,
            "edge_dilate": 0,
            "edge_erode": 0,
        },
        "Advanced": {
            "preset": "Advanced",
            "bilateral_passes": 3,
            "bilateral_d": 11,
            "bilateral_sigmaColor": 120,
            "bilateral_sigmaSpace": 120,
            "quant_method": "KMeans",
            "kmeans_k": 10,
            "edge_method": "Canny",
            "canny_t1": 70,
            "canny_t2": 160,
            "edge_median_ksize": 7,
            "edge_dilate": 2,
            "edge_erode": 1,
        },
        "Anime": {
            "preset": "Anime",
            "bilateral_passes": 2,
            "bilateral_d": 7,
            "bilateral_sigmaColor": 90,
            "bilateral_sigmaSpace": 90,
            "quant_method": "Downscale+Uniform",
            "bits": 3,
            "downscale_factor": 0.25,
            "edge_method": "Adaptive",
            "adaptive_block": 11,
            "adaptive_C": 1,
            "edge_median_ksize": 5,
            "edge_dilate": 1,
            "edge_erode": 0,
        },
        "Whole": {
            "preset": "Whole",
            "bilateral_passes": 1,
            "bilateral_d": 9,
            "bilateral_sigmaColor": 80,
            "bilateral_sigmaSpace": 80,
            "quant_method": "Downscale+Uniform",
            "bits": 3,
            "downscale_factor": 0.2,
            "edge_method": "Adaptive",
            "adaptive_block": 9,
            "adaptive_C": 2,
            "edge_median_ksize": 5,
            "edge_dilate": 0,
            "edge_erode": 0,
        },
    }

    # Parameter spec for UIs
    parameters = [
        {"name": "preset", "label": "Preset", "type": "str", "default": "Detailed",
         "options": ["Detailed", "Fast", "Advanced", "Anime", "Whole"]},
        # Smoothing
        {"name": "bilateral_passes", "label": "Bilateral Passes",
            "type": "int", "default": 2, "min": 0, "max": 4, "step": 1},
        {"name": "bilateral_d", "label": "Bilateral Diameter",
            "type": "int", "default": 9, "min": 1, "max": 25, "step": 1},
        {"name": "bilateral_sigmaColor", "label": "Sigma Color",
            "type": "int", "default": 75, "min": 1, "max": 200, "step": 1},
        {"name": "bilateral_sigmaSpace", "label": "Sigma Space",
            "type": "int", "default": 75, "min": 1, "max": 200, "step": 1},

        # Quantization
        {"name": "quant_method", "label": "Quantization Method", "type": "str", "default": "Uniform",
         "options": ["Uniform", "MeanShift", "Downscale+Uniform", "KMeans"]},
        {"name": "bits", "label": "Color Bits (Uniform/Downscale)",
         "type": "int", "default": 4, "min": 2, "max": 8, "step": 1},
        {"name": "downscale_factor", "label": "Downscale Factor",
            "type": "float", "default": 0.25, "min": 0.1, "max": 1.0, "step": 0.05},
        {"name": "meanshift_spatial", "label": "Mean Shift Spatial",
            "type": "int", "default": 10, "min": 1, "max": 30, "step": 1},
        {"name": "meanshift_color", "label": "Mean Shift Color",
            "type": "int", "default": 30, "min": 1, "max": 100, "step": 1},
        {"name": "kmeans_k", "label": "KMeans Clusters",
            "type": "int", "default": 8, "min": 2, "max": 16, "step": 1},
        {"name": "kmeans_attempts", "label": "KMeans Attempts",
            "type": "int", "default": 3, "min": 1, "max": 20, "step": 1},
        {"name": "kmeans_max_iter", "label": "KMeans Max Iter",
            "type": "int", "default": 20, "min": 1, "max": 200, "step": 1},
        {"name": "kmeans_eps", "label": "KMeans Eps", "type": "float",
            "default": 0.001, "min": 1e-6, "max": 1.0, "step": 0.001},
        {"name": "seed", "label": "Random Seed", "type": "int",
            "default": 1234, "min": 0, "max": 2**31-1, "step": 1},

        # Edges
        {"name": "edge_method", "label": "Edge Method", "type": "str", "default": "Adaptive",
         "options": ["Adaptive", "Canny", "Sobel", "Laplacian"]},
        {"name": "adaptive_block", "label": "Adaptive BlockSize",
            "type": "int", "default": 9, "min": 3, "max": 31, "step": 2},
        {"name": "adaptive_C", "label": "Adaptive C",
            "type": "int", "default": 2, "min": -20, "max": 20, "step": 1},
        {"name": "canny_t1", "label": "Canny Threshold 1",
            "type": "int", "default": 100, "min": 0, "max": 500, "step": 1},
        {"name": "canny_t2", "label": "Canny Threshold 2",
            "type": "int", "default": 200, "min": 0, "max": 500, "step": 1},
        {"name": "edge_median_ksize", "label": "Edge MedianBlur k",
            "type": "int", "default": 7, "min": 3, "max": 11, "step": 2},

        # Morphology on edges
        {"name": "edge_dilate",
            "label": "Dilate Edges (px)", "type": "int", "default": 0, "min": 0, "max": 3, "step": 1},
        {"name": "edge_erode",
            "label": "Erode Edges (px)", "type": "int", "default": 0, "min": 0, "max": 3, "step": 1},

        # Output
        {"name": "preserve_alpha", "label": "Preserve Alpha",
            "type": "bool", "default": True},
        {"name": "anti_alias_upscale", "label": "AA on Upscale",
            "type": "bool", "default": True},
    ]

    def define_parameters(self):
        return self.parameters

    def apply(self, image: np.ndarray, params: Optional[Dict[str, Any]] = None, **kwargs) -> np.ndarray:
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid NumPy array")
        img_in = _ensure_uint8(image)

        bgr, alpha = _split_alpha(img_in)  # work in BGR
        # Merge keyword args (used by legacy callers) into params
        raw_params: Dict[str, Any] = {}
        if params:
            raw_params.update(params)
        if kwargs:
            raw_params.update(kwargs)

        migrated_params = self._migrate_params(raw_params)
        original_keys = set(raw_params.keys())
        preset = migrated_params.get(
            "preset") or self.current_variant or self.default_variant
        migrated_params["preset"] = preset
        if "preset" in original_keys:
            provided_keys = set(original_keys)
        else:
            # preset not included if inferred
            provided_keys = set(original_keys)
        self.current_variant = preset
        p = self._p(migrated_params, provided_keys)

        # 1) smoothing passes to keep edges while denoising
        smooth = bgr.copy()
        for _ in range(p["bilateral_passes"]):
            smooth = cv2.bilateralFilter(
                smooth, p["bilateral_d"], p["bilateral_sigmaColor"], p["bilateral_sigmaSpace"]
            )

        # 2) quantization
        q = self._quantize(smooth, p)

        # 3) edges
        edges = self._edges(bgr, p)

        # optional morphology clean-up
        if p["edge_dilate"] > 0:
            k = cv2.getStructuringElement(
                cv2.MORPH_RECT, (p["edge_dilate"], p["edge_dilate"]))
            edges = cv2.dilate(edges, k)
        if p["edge_erode"] > 0:
            k = cv2.getStructuringElement(
                cv2.MORPH_RECT, (p["edge_erode"], p["edge_erode"]))
            edges = cv2.erode(edges, k)

        # 4) combine: we want black edges on quantized color (mask = edges==255)
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        cartoon = cv2.bitwise_and(q, edges_colored)

        out = _merge_alpha(cartoon, alpha if p["preserve_alpha"] else None)
        return out

    # ------- helpers -------

    def _migrate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map legacy parameter names/values to the new unified schema.
        Returns a new dict without mutating the input.
        """
        if not params:
            return {}

        migrated: Dict[str, Any] = {}
        preset_hint: Optional[str] = None

        # Legacy Cartoon (Detailed) params
        if any(k.startswith("bilateral_filter_") or k.startswith("canny_") for k in params):
            preset_hint = preset_hint or "Detailed"
            mapping = {
                "bilateral_filter_diameter": "bilateral_d",
                "bilateral_filter_sigmaColor": "bilateral_sigmaColor",
                "bilateral_filter_sigmaSpace": "bilateral_sigmaSpace",
                "canny_threshold1": "canny_t1",
                "canny_threshold2": "canny_t2",
            }
            for old, new in mapping.items():
                if old in params:
                    migrated[new] = params[old]
            if "color_levels" in params:
                levels = max(2, min(16, int(params["color_levels"])))
                bits = max(2, min(8, int(round(np.log2(levels))))
                           ) if levels > 0 else 4
                migrated["bits"] = bits

        # Legacy Cartoon (Fast) params
        if any(k in params for k in ("spatial_radius", "color_radius", "downscale")):
            preset_hint = preset_hint or "Fast"
            if "quant_method" in params:
                method_map = {
                    "Uniform": "Uniform",
                    "Mean Shift": "MeanShift",
                    "Downscale+Quantize": "Downscale+Uniform",
                    "K-means": "KMeans",
                }
                migrated["quant_method"] = method_map.get(
                    params["quant_method"], "Uniform")
            if "spatial_radius" in params:
                migrated["meanshift_spatial"] = params["spatial_radius"]
            if "color_radius" in params:
                migrated["meanshift_color"] = params["color_radius"]
            if "downscale" in params:
                migrated["downscale_factor"] = params["downscale"]
            if "bits" in params:
                migrated["bits"] = params["bits"]

        # Legacy Advanced Cartoon params
        if "edge_threshold1" in params or "edge_method" in params:
            preset_hint = preset_hint or "Advanced"
            migrated["edge_method"] = params.get(
                "edge_method", migrated.get("edge_method"))
            migrated["canny_t1"] = params.get(
                "edge_threshold1", migrated.get("canny_t1"))
            migrated["canny_t2"] = params.get(
                "edge_threshold2", migrated.get("canny_t2"))
            if "sharpen_intensity" in params:
                migrated["edge_dilate"] = 1 if params["sharpen_intensity"] > 1.2 else 0
            if "enable_color_quantization" in params and params["enable_color_quantization"]:
                migrated["quant_method"] = "KMeans"
                migrated["kmeans_k"] = params.get(
                    "color_clusters", migrated.get("kmeans_k"))
            if params.get("enable_texture_overlay"):
                migrated["preset"] = "Advanced"
            if "texture_alpha" in params:
                migrated["edge_erode"] = int(params["texture_alpha"] * 2)

        # Legacy Anime variant hints
        if "anime_mode" in params or "enable_bloom_effect" in params:
            preset_hint = preset_hint or "Anime"
            migrated["quant_method"] = "Downscale+Uniform"
            migrated["downscale_factor"] = min(
                0.4, params.get("downscale_factor", 0.25))
            migrated["bilateral_passes"] = max(
                2, params.get("bilateral_filter_diameter", 9) // 6)
            migrated["edge_method"] = "Adaptive"

        if preset_hint and "preset" not in params:
            migrated["preset"] = preset_hint

        # Copy over any keys already in new schema
        for key in params:
            if key in {spec["name"] for spec in self.parameters}:
                migrated[key] = params[key]

        return migrated

    def _p(self, params: Optional[Dict[str, Any]], provided_keys: Optional[set] = None) -> Dict[str, Any]:
        # Build defaults from spec
        spec_defaults = {s["name"]: s.get("default") for s in self.parameters}
        p = {**spec_defaults}

        # Accept both dict input and keyword params (the latter via **kwargs path)
        if params:
            if isinstance(params, dict):
                p.update(params)
            else:
                raise ValueError("Parameters must be provided as a dict.")

        # Apply preset defaults when values were not explicitly provided
        spec_lookup = {s["name"]: s for s in self.parameters}
        preset = p.get("preset", spec_defaults.get("preset", "Detailed"))
        preset_defaults = self.PRESET_DEFAULTS.get(preset, {})
        provided_keys = provided_keys or set()
        for key, value in preset_defaults.items():
            if key not in provided_keys and key in spec_defaults:
                p[key] = value
        self.current_variant = preset

        # Validate ranges
        def clamp(name, lo, hi, cast=None):
            v = p.get(name, spec_defaults[name])
            if cast is None:
                spec = spec_lookup.get(name)
                cast_type = spec.get("type") if spec else None
                if cast_type == "int":
                    cast = int
                elif cast_type == "float":
                    cast = float
                elif cast_type == "bool":
                    def bool_cast(val):
                        if isinstance(val, bool):
                            return val
                        if isinstance(val, (int, float)):
                            return bool(val)
                        return str(val).strip().lower() in {"1", "true", "yes", "on"}
                    cast = bool_cast
            if cast:
                try:
                    v = cast(v)
                except Exception:
                    v = cast(spec_defaults[name])
            if v < lo:
                v = lo
            elif v > hi:
                v = hi
            p[name] = v

        clamp("bilateral_passes", 0, 4, int)
        clamp("bilateral_d", 1, 25, int)
        clamp("bilateral_sigmaColor", 1, 200, int)
        clamp("bilateral_sigmaSpace", 1, 200, int)
        if p["quant_method"] not in ["Uniform", "MeanShift", "Downscale+Uniform", "KMeans"]:
            p["quant_method"] = spec_defaults["quant_method"]
        clamp("bits", 2, 8, int)
        clamp("downscale_factor", 0.1, 1.0, float)
        clamp("meanshift_spatial", 1, 30, int)
        clamp("meanshift_color", 1, 100, int)
        clamp("kmeans_k", 2, 16, int)
        clamp("kmeans_attempts", 1, 20, int)
        clamp("kmeans_max_iter", 1, 200, int)
        clamp("kmeans_eps", 1e-6, 1.0, float)

        if p["edge_method"] not in ["Adaptive", "Canny", "Sobel", "Laplacian"]:
            p["edge_method"] = spec_defaults["edge_method"]
        # odd kernel for median; clamp to nearest odd within range
        k = int(p["edge_median_ksize"])
        k = max(3, min(11, k))
        if k % 2 == 0:
            k += 1 if k < 11 else -1
        p["edge_median_ksize"] = k
        clamp("adaptive_block", 3, 31, int)
        if p["adaptive_block"] % 2 == 0:
            p["adaptive_block"] += 1
        clamp("adaptive_C", -20, 20, int)
        clamp("canny_t1", 0, 500, int)
        clamp("canny_t2", 0, 500, int)

        p["preserve_alpha"] = bool(p["preserve_alpha"])
        p["anti_alias_upscale"] = bool(p["anti_alias_upscale"])
        p["seed"] = int(p["seed"])
        return p

    def _quantize(self, img: np.ndarray, p: Dict[str, Any]) -> np.ndarray:
        method = p["quant_method"]
        if method == "Uniform":
            return self._uniform_bits(img, p["bits"])
        elif method == "MeanShift":
            base = cv2.pyrMeanShiftFiltering(
                img, p["meanshift_spatial"], p["meanshift_color"])
            return base
        elif method == "Downscale+Uniform":
            return self._downscale_uniform(img, p["bits"], p["downscale_factor"], p["anti_alias_upscale"])
        elif method == "KMeans":
            return self._kmeans_quant(img,
                                      k=p["kmeans_k"],
                                      attempts=p["kmeans_attempts"],
                                      max_iter=p["kmeans_max_iter"],
                                      eps=p["kmeans_eps"],
                                      seed=p["seed"])
        return img

    @staticmethod
    def _uniform_bits(img: np.ndarray, bits: int) -> np.ndarray:
        # e.g., bits=4 -> keep high 4 bits: 0xF0 buckets; add half bin for mid-tone pop
        shift = 8 - bits
        quant = (img >> shift) << shift
        quant = quant + (1 << (shift - 1)) if shift > 0 else quant
        return np.clip(quant, 0, 255).astype(np.uint8)

    @staticmethod
    def _downscale_uniform(img: np.ndarray, bits: int, scale: float, aa: bool) -> np.ndarray:
        h, w = img.shape[:2]
        interp_down = cv2.INTER_AREA if aa else cv2.INTER_LINEAR
        small = cv2.resize(
            img, (int(w * scale), int(h * scale)), interpolation=interp_down)
        quant = CartoonStylePro._uniform_bits(small, bits)
        interp_up = cv2.INTER_LINEAR if aa else cv2.INTER_NEAREST
        up = cv2.resize(quant, (w, h), interpolation=interp_up)
        return up

    @staticmethod
    def _kmeans_quant(img: np.ndarray, k: int, attempts: int, max_iter: int, eps: float, seed: int) -> np.ndarray:
        data = np.float32(img.reshape((-1, 3)))
        criteria = (cv2.TERM_CRITERIA_EPS +
                    cv2.TERM_CRITERIA_MAX_ITER, int(max_iter), float(eps))
        rng = cv2.RNG(seed)
        compactness, labels, centers = cv2.kmeans(
            data, k, None, criteria, attempts, cv2.KMEANS_PP_CENTERS
        )
        centers = np.uint8(centers)
        quant = centers[labels.flatten()].reshape(img.shape)
        return quant

    def _edges(self, img_bgr: np.ndarray, p: Dict[str, Any]) -> np.ndarray:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, p["edge_median_ksize"])
        if p["edge_method"] == "Adaptive":
            edges = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY,
                p["adaptive_block"], p["adaptive_C"]
            )
        elif p["edge_method"] == "Sobel":
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            sobel = cv2.magnitude(sobelx, sobely)
            edges = cv2.normalize(sobel, None, 0, 255,
                                  cv2.NORM_MINMAX).astype(np.uint8)
            _, edges = cv2.threshold(
                edges, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        elif p["edge_method"] == "Laplacian":
            lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
            edges = cv2.convertScaleAbs(lap)
            _, edges = cv2.threshold(
                edges, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        else:
            edges = cv2.Canny(gray, p["canny_t1"], p["canny_t2"])
            # Convert to binary (white edges on black background)
            edges = cv2.threshold(edges, 0, 255, cv2.THRESH_BINARY)[1]
        return edges


# ---- Optional: drop-in compatibility shims for your existing code ----


class Cartoon(Style):
    """Back-compat wrapper approximating your original 'Cartoon (Detailed)'."""

    def __init__(self):
        super().__init__()
        self.name = "Cartoon (Detailed)"
        self.category = "Artistic"
        self._pro = CartoonStylePro()

    def define_parameters(self):
        # Map to Pro parameters for UI continuity
        return {
            "bilateral_filter_diameter": {"default": 9, "min": 1, "max": 20, "label": "Bilateral Diameter", "step": 1},
            "bilateral_filter_sigmaColor": {"default": 75, "min": 1, "max": 150, "label": "Sigma Color", "step": 1},
            "bilateral_filter_sigmaSpace": {"default": 75, "min": 1, "max": 150, "label": "Sigma Space", "step": 1},
            "canny_threshold1": {"default": 100, "min": 0, "max": 500, "label": "Canny Threshold 1", "step": 1},
            "canny_threshold2": {"default": 200, "min": 0, "max": 500, "label": "Canny Threshold 2", "step": 1},
            "color_levels": {"default": 8, "min": 2, "max": 16, "label": "Color Levels", "step": 1},
        }

    def apply(self, image, params=None):
        # Translate to Pro params and run
        p_def = self.define_parameters()
        p = {k: (params.get(k, v["default"]) if params else v["default"])
             for k, v in p_def.items()}
        # emulate your pipeline: bilateral + Canny + uniform quantization via levels
        levels = int(np.clip(p["color_levels"], 2, 16))
        bits = int(np.rint(np.log2(levels)))  # approx mapping
        pro_params = dict(
            preset="Detailed",
            bilateral_passes=1,
            bilateral_d=int(np.clip(p["bilateral_filter_diameter"], 1, 20)),
            bilateral_sigmaColor=int(
                np.clip(p["bilateral_filter_sigmaColor"], 1, 150)),
            bilateral_sigmaSpace=int(
                np.clip(p["bilateral_filter_sigmaSpace"], 1, 150)),
            quant_method="Uniform",
            bits=int(np.clip(max(2, bits), 2, 8)),
            edge_method="Canny",
            canny_t1=int(np.clip(p["canny_threshold1"], 0, 500)),
            canny_t2=int(np.clip(p["canny_threshold2"], 0, 500)),
            edge_median_ksize=7,
            preserve_alpha=True,
            anti_alias_upscale=True,
            downscale_factor=0.25, meanshift_spatial=10, meanshift_color=30,
            kmeans_k=8, kmeans_attempts=3, kmeans_max_iter=20, kmeans_eps=0.001, seed=1234,
            adaptive_block=9, adaptive_C=2, edge_dilate=1, edge_erode=0
        )
        return self._pro.apply(image, pro_params)

    # keep your helper for parity
    def quantize_colors(self, image: np.ndarray, k: int) -> np.ndarray:
        return CartoonStylePro._kmeans_quant(_ensure_uint8(image), k, attempts=5, max_iter=30, eps=1e-3, seed=1234)


class CartoonStyle(Style):
    """Back-compat wrapper approximating your 'Cartoon (Fast)' with multiple methods."""
    name = "Cartoon (Fast)"
    category = "Artistic"

    def __init__(self):
        super().__init__()
        self._pro = CartoonStylePro()

    parameters = [
        {"name": "quant_method", "label": "Quantization Method", "type": "str",
         "default": "Uniform", "options": ["Uniform", "Mean Shift", "Downscale+Quantize", "K-means"]},
        {"name": "bits", "label": "Color Bits (Uniform/Downscale)",
         "type": "int", "default": 4, "min": 2, "max": 8},
        {"name": "spatial_radius", "label": "Mean Shift Spatial Radius",
            "type": "int", "default": 10, "min": 1, "max": 30},
        {"name": "color_radius", "label": "Mean Shift Color Radius",
            "type": "int", "default": 30, "min": 1, "max": 100},
        {"name": "k", "label": "K-means Clusters",
            "type": "int", "default": 8, "min": 2, "max": 16},
        {"name": "downscale", "label": "Downscale Factor (Downscale+Quantize)",
         "type": "float", "default": 0.25, "min": 0.1, "max": 1.0},
    ]

    def apply(self, img, params):
        # Map to Pro and delegate
        method_map = {
            "Uniform": "Uniform",
            "Mean Shift": "MeanShift",
            "Downscale+Quantize": "Downscale+Uniform",
            "K-means": "KMeans",
        }
        p = {
            "preset": "Fast",
            "quant_method": method_map.get(params.get("quant_method", "Uniform"), "Uniform"),
            "bits": int(params.get("bits", 4)),
            "meanshift_spatial": int(params.get("spatial_radius", 10)),
            "meanshift_color": int(params.get("color_radius", 30)),
            "kmeans_k": int(params.get("k", 8)),
            "downscale_factor": float(params.get("downscale", 0.25)),
            # sensible defaults for rest
            "bilateral_passes": 1, "bilateral_d": 9, "bilateral_sigmaColor": 75, "bilateral_sigmaSpace": 75,
            "edge_method": "Adaptive", "adaptive_block": 9, "adaptive_C": 2,
            "edge_median_ksize": 7, "edge_dilate": 0, "edge_erode": 0,
            "kmeans_attempts": 3, "kmeans_max_iter": 20, "kmeans_eps": 0.001, "seed": 1234,
            "preserve_alpha": True, "anti_alias_upscale": True,
            "canny_t1": 100, "canny_t2": 200,
        }
        return self._pro.apply(img, p)
