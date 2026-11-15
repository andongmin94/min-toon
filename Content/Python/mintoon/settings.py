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


def asset_paths(root: str) -> tuple[str, str, str]:
    """This initial tool writes only to named ASCII folders beneath /Game."""
    if not re.fullmatch(r"/Game(?:/[A-Za-z0-9_]+)+", root):
        raise ValueError("Use a project path such as /Game/MinToon (letters, digits and underscores).")
    return tuple(f"{root}/{name}" for name in ("TP_MinToon", "M_MinToon", "MI_MinToon"))


def require_target_version(version: str) -> None:
    if re.match(r"^5\.8\.", version) is None:
        raise RuntimeError(f"MinToon currently targets UE 5.8 only; running {version}.")
