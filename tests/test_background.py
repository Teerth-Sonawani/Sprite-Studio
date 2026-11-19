"""Background removal and alpha-cleanup tests."""

from __future__ import annotations

from PIL import Image, ImageDraw

from sprite_studio.background import (
    clean_transparency,
    remove_background,
    suggest_background_colors,
)

CHROMA = (194, 24, 91, 255)
GREEN = (80, 140, 90, 255)


def _subject_on_chroma() -> Image.Image:
    image = Image.new("RGBA", (16, 16), CHROMA)
    ImageDraw.Draw(image).rectangle((4, 4, 11, 11), fill=GREEN)
    return image


def test_edge_removal_keeps_isolated_subject():
    image = _subject_on_chroma()
    result, report = remove_background(image, tolerance=20, border=2, method="edge")
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((4, 4)) == GREEN
    assert report["method"] == "edge"
    assert report["removed_pixels"] > 0
    assert report["remaining_visible_pixels"] == 64


def test_edge_removal_protects_enclosed_backdrop_colour():
    image = _subject_on_chroma()
    image.putpixel((7, 7), CHROMA)  # e.g. a gem or eye sharing the key colour
    edge_result, _ = remove_background(image, tolerance=20, border=2, method="edge")
    global_result, _ = remove_background(image, tolerance=20, border=2, method="global")
    assert edge_result.getpixel((7, 7))[3] == 255
    assert global_result.getpixel((7, 7))[3] == 0


def test_method_none_removes_nothing():
    image = _subject_on_chroma()
    result, report = remove_background(image, method="none")
    assert result.tobytes() == image.tobytes()
    assert report["removed_pixels"] == 0


def test_suggest_background_colours_finds_chroma():
    suggestions = suggest_background_colors(_subject_on_chroma(), border=2, tolerance=20)
    assert suggestions
    assert suggestions[0]["rgb"] == [194, 24, 91]


def test_invalid_method_rejected():
    import pytest

    with pytest.raises(ValueError):
        remove_background(_subject_on_chroma(), method="magic")


def test_clean_transparency_removes_tiny_island():
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((2, 2, 10, 10), fill=GREEN)
    image.putpixel((14, 14), GREEN)
    cleaned, report = clean_transparency(image, min_island=4)
    assert cleaned.getpixel((14, 14))[3] == 0
    assert cleaned.getpixel((2, 2))[3] == 255
    assert report["removed_component_count"] == 1
    assert report["removed_pixels"] == 1


def test_clean_transparency_preserves_largest_island_even_below_threshold():
    image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    image.putpixel((3, 3), GREEN)
    cleaned, report = clean_transparency(image, min_island=10, preserve_largest=True)
    assert cleaned.getpixel((3, 3))[3] == 255
    assert report["removed_component_count"] == 0


def test_fill_holes_makes_enclosed_transparency_opaque():
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((2, 2, 13, 13), outline=GREEN, width=3)
    assert image.getpixel((8, 8))[3] == 0
    filled, report = clean_transparency(image, min_island=4, fill_holes=True)
    assert filled.getpixel((8, 8))[3] == 255
    assert report["filled_hole_pixels"] >= 1


def test_alpha_floor_removes_faint_pixels():
    image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    image.putpixel((1, 1), (10, 20, 30, 5))
    image.putpixel((2, 2), GREEN)
    cleaned, _ = clean_transparency(image, min_island=0, alpha_floor=10)
    assert cleaned.getpixel((1, 1))[3] == 0
    assert cleaned.getpixel((2, 2))[3] == 255
