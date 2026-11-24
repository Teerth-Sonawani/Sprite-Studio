"""Deterministic mock provider for tests and offline dry runs.

It produces a small original geometric sprite; it is not a substitute for art
review and is never labelled as a generated production asset.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

from sprite_studio.errors import UsageError
from sprite_studio.image_utils import save_png
from sprite_studio.providers.base_provider import (
    GenerationRequest,
    GenerationResult,
    ImageProvider,
    ModelInfo,
    ProviderHealth,
)


class MockProvider(ImageProvider):
    provider_id = "mock"

    def __init__(self, output_dir: str | Path = "mock_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(True, self.provider_id, "offline", "Mock provider is ready; no network or credits used.", 1, 0, [])

    def list_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_key="mock-shape-v1",
                display_name="Mock Shape v1",
                modality="image",
                operations=["image_generation"],
                input_schema={"type": "object", "properties": {"prompt": {"type": "string"}, "seed": {"type": "integer"}}},
                limits={"max_n": 4, "sizes": ["64x64", "128x128"]},
                price=0,
                price_unit="image",
            )
        ]

    def estimate_cost(self, request: GenerationRequest) -> dict:
        return {"model_key": request.model_key or "mock-shape-v1", "operation": request.operation, "estimated_credits": 0, "currency": "mock"}

    def generate(self, request: GenerationRequest) -> GenerationResult:
        errors = request.validate()
        if errors:
            raise UsageError("; ".join(errors))
        seed = int((request.parameters or {}).get("seed", 0)) or int(hashlib.sha256(request.prompt.encode()).hexdigest()[:8], 16)
        width = int((request.parameters or {}).get("width", 128))
        height = int((request.parameters or {}).get("height", 128))
        if width > 512 or height > 512 or width < 8 or height < 8:
            raise UsageError("mock dimensions must be between 8 and 512")
        image = self._draw(seed, width, height)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"mock_{seed}_{width}x{height}.png"
        save_png(image, path, overwrite=True)
        return GenerationResult(
            provider=self.provider_id,
            mode="offline",
            status="succeeded",
            generation_id=f"mock-{seed}",
            model_key="mock-shape-v1",
            outputs=[{"url": f"file://{path.resolve()}", "path": str(path), "width": width, "height": height}],
            estimated_credits=0,
            reserved_credits=0,
            charged_credits=0,
            raw={"mock": True, "prompt": request.prompt},
        )

    def get_status(self, generation_id: str) -> GenerationResult:
        return GenerationResult(provider=self.provider_id, mode="offline", status="succeeded", generation_id=generation_id)

    def download_result(self, result: GenerationResult, destination: str | Path) -> list[Path]:
        destination = Path(destination)
        saved = []
        for i, output in enumerate(result.outputs):
            src = output.get("path")
            if not src:
                continue
            src = Path(src)
            if destination.suffix.lower() == ".png":
                target = destination
            else:
                destination.mkdir(parents=True, exist_ok=True)
                target = destination / f"{result.generation_id or 'mock'}_{i:02d}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(src.read_bytes())
            saved.append(target)
        return saved

    def capabilities(self) -> dict:
        return {
            "provider": self.provider_id,
            "modes": ["offline"],
            "list_models": True,
            "estimate_cost": True,
            "generate": True,
            "get_status": True,
            "download_result": True,
            "async": False,
            "reference_images": False,
            "transparent_background": True,
            "manual_handoff": False,
        }

    @staticmethod
    def _draw(seed: int, width: int, height: int) -> Image.Image:
        # Original, deliberately simple geometry with a readable silhouette.
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        rng = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        hue = rng % 360
        import colorsys

        r, g, b = colorsys.hsv_to_rgb(hue / 360, 0.62, 0.82)
        color = (int(r * 255), int(g * 255), int(b * 255), 255)
        dark = (int(r * 180), int(g * 180), int(b * 190), 255)
        cx, cy = width // 2, height // 2 + height // 12
        radius = min(width, height) // 3
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color, outline=dark, width=max(2, width // 32))
        draw.ellipse([cx - radius // 3, cy - radius // 4, cx - radius // 8, cy + radius // 12], fill=(20, 24, 32, 255))
        draw.ellipse([cx + radius // 8, cy - radius // 4, cx + radius // 3, cy + radius // 12], fill=(20, 24, 32, 255))
        return image
