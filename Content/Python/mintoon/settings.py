"""User-editable initial values. No Unreal dependency; no runtime renderer here."""
from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class ToonSettings:
    # RGB is linear, not sRGB. The native profile factory supplies the ramps.
    base_color: tuple[float, float, float] = (0.65, 0.35, 0.18)
    roughness: float = 0.6
    specular: float = 0.35
    anisotropy: float = 0.0
    diffuse_indirect_scale: float = 0.35
    specular_indirect_scale: float = 0.2

    def __post_init__(self) -> None:
        if len(self.base_color) != 3:
            raise ValueError("base_color must contain three linear RGB components.")
        for index, value in enumerate(self.base_color):
            _number_in_range(f"base_color[{index}]", value, 0.0, 1.0)
        object.__setattr__(self, "base_color", tuple(self.base_color))
        _number_in_range("roughness", self.roughness, 0.0, 1.0)
        _number_in_range("specular", self.specular, 0.0, 1.0)
        _number_in_range("anisotropy", self.anisotropy, -1.0, 1.0)
        for name in ("diffuse_indirect_scale", "specular_indirect_scale"):
            _number_in_range(name, getattr(self, name), 0.0, math.inf)


def _number_in_range(name: str, value: float, minimum: float, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be finite and between {minimum} and {maximum}.")


Rgb = tuple[float, float, float]


@dataclass(frozen=True)
class ToonPart:
    """Look of one surface group. Ramps are (N·L input, linear RGB output) keys."""

    name: str
    diffuse_ramp: tuple[tuple[float, Rgb], ...]
    specular_ramp: tuple[tuple[float, float], ...]
    diffuse_indirect_scale: float
    specular_indirect_scale: float
    roughness: float
    specular: float
    rim_strength: float
    outline_width: float  # centimetres, world space

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9]+", self.name):
            raise ValueError("Part names use ASCII letters and digits only.")
        _keys_in_order("diffuse_ramp", [time for time, _ in self.diffuse_ramp])
        _keys_in_order("specular_ramp", [time for time, _ in self.specular_ramp])
        for time, rgb in self.diffuse_ramp:
            for value in rgb:
                _number_in_range("diffuse_ramp value", value, 0.0, 1.0)
        for _, value in self.specular_ramp:
            _number_in_range("specular_ramp value", value, 0.0, 1.0)
        for field in ("roughness", "specular", "rim_strength"):
            _number_in_range(field, getattr(self, field), 0.0, 1.0)
        for field in ("diffuse_indirect_scale", "specular_indirect_scale", "outline_width"):
            _number_in_range(field, getattr(self, field), 0.0, math.inf)


def _keys_in_order(name: str, times: list[float]) -> None:
    if len(times) < 2:
        raise ValueError(f"{name} needs at least two keys.")
    for time in times:
        _number_in_range(f"{name} time", time, 0.0, 1.0)
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError(f"{name} key times must increase strictly.")


# Starting looks, checked in the VRM validation scene (Tests/create_vrm_scene.py). Ramp input is
# half-Lambert (N·L*0.5+0.5) times shadow, so 0.5 is the terminator. Fully shadowed areas get no
# direct light at all, only sky light scaled by diffuse_indirect_scale; keep a sky light in the level.
# The face switches far behind the terminator so most of it stays lit, as in anime character art.
PARTS = {
    part.name: part
    for part in (
        ToonPart("Body", ((0.0, (0.62, 0.50, 0.55)), (0.42, (0.62, 0.50, 0.55)), (0.47, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))),
                 ((0.0, 0.0), (0.92, 0.0), (0.94, 0.6), (1.0, 0.6)), 0.65, 0.15, 0.6, 0.25, 0.20, 0.20),
        ToonPart("Face", ((0.0, (0.84, 0.70, 0.70)), (0.18, (0.84, 0.70, 0.70)), (0.24, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))),
                 ((0.0, 0.0), (1.0, 0.0)), 0.80, 0.10, 0.8, 0.10, 0.10, 0.12),
        ToonPart("Hair", ((0.0, (0.55, 0.47, 0.58)), (0.40, (0.55, 0.47, 0.58)), (0.45, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))),
                 ((0.0, 0.0), (0.78, 0.0), (0.80, 1.0), (1.0, 1.0)), 0.65, 0.20, 0.35, 0.50, 0.25, 0.20),
        ToonPart("Background", ((0.0, (0.42, 0.47, 0.60)), (0.30, (0.42, 0.47, 0.60)), (0.36, (0.74, 0.75, 0.82)),
                                (0.62, (0.74, 0.75, 0.82)), (0.68, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))),
                 ((0.0, 0.0), (1.0, 0.0)), 1.00, 0.20, 0.8, 0.10, 0.0, 0.8),
    )
}

# Texture and colour parameters that hold the albedo in common importers (VRM4U MToon/glTF,
# engine templates). Matching is case-insensitive; the first match in this order wins.
BASE_TEXTURE_NAMES = ("mtoon_tex_MainTex", "gltf_tex_diffuse", "BaseColorTexture", "BaseColor", "Albedo", "Diffuse")
BASE_COLOR_NAMES = ("mtoon_Color", "gltf_basecolor", "BaseColor", "Color", "Tint")


def classify_slot(slot_name: str) -> str:
    """Pick a character part from a material slot name (VRoid/VRM conventions)."""
    name = slot_name.lower()
    if "hair" in name:
        return "Hair"
    if any(key in name for key in ("face", "eye", "mouth", "brow", "lash", "teeth", "tongue")):
        return "Face"
    return "Body"


def pick_name(available, preferred) -> str | None:
    """Return the available parameter that best matches the preferred names."""
    names = [str(name) for name in available]
    for wanted in preferred:
        for name in names:
            if name.lower() == wanted.lower():
                return name
    for wanted in preferred:
        for name in names:
            if wanted.lower() in name.lower():
                return name
    return None


def safe_asset_name(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", text).strip("_")
    return cleaned[:48] or "Slot"


def color_ramp_text(keys) -> str:
    """Unreal text for FRuntimeCurveLinearColor RGB curves (verified format in UE 5.8)."""
    curves = []
    for channel in range(3):
        points = ",".join(f"(Time={t:.6f},Value={rgb[channel]:.6f})" for t, rgb in keys)
        curves.append(f"ColorCurves[{channel}]=(Keys=({points}))")
    return "(" + ",".join(curves) + ")"


def profile_text(part: ToonPart) -> str:
    specular = tuple((t, (v, v, v)) for t, v in part.specular_ramp)
    return (
        f"(DiffuseRamp={color_ramp_text(part.diffuse_ramp)},"
        f"SpecularRamp={color_ramp_text(specular)},"
        f"DiffuseIndirectScale={part.diffuse_indirect_scale:.6f},"
        f"SpecularIndirectScale={part.specular_indirect_scale:.6f},"
        # Shadowed areas take the ramp's tinted shadow tone instead of going black.
        "bDiffuseRampIncludeShadow=True)"
    )


def asset_paths(root: str) -> tuple[str, str, str]:
    """This initial tool writes only to named ASCII folders beneath /Game."""
    require_root(root)
    return tuple(f"{root}/{name}" for name in ("TP_MinToon", "M_MinToon", "MI_MinToon"))


def require_root(root: str) -> None:
    if not re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)+", root):
        raise ValueError("Use a project path such as /Game/MinToon (letters, digits and underscores).")


def require_target_version(version: str) -> None:
    if re.match(r"^5\.8\.", version) is None:
        raise RuntimeError(f"MinToon currently targets UE 5.8 only; running {version}.")
