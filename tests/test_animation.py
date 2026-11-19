"""Frame alignment, animation validation and preview tests."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from sprite_studio.animation import align_frames, make_preview, validate_animation
from sprite_studio.image_utils import alpha_bbox


def _bob_frame(offset: int) -> Image.Image:
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((3, 5 + offset, 12, 13 + offset), fill=(80, 140, 90, 255))
    return image


def _subtle_frame(step: int) -> Image.Image:
    """Frames that differ by one highlight pixel, so loop difference stays small."""

    image = _bob_frame(0)
    ImageDraw.Draw(image).point((5 + step, 8), fill=(240, 230, 200, 255))
    return image


def test_align_frames_plants_bottom_centre():
    frames = [_bob_frame(0), _bob_frame(2), _bob_frame(1)]
    aligned, report = align_frames(frames, canvas_width=20, canvas_height=20, pivot_x=10, pivot_y=18)
    for frame in aligned:
        assert alpha_bbox(frame)[3] == 17  # pivot_y - 1
    assert report["canvas"] == {"width": 20, "height": 20}
    assert report["align"] == "bottom-center"


def test_align_none_preserves_authored_offset():
    frames = [_bob_frame(0), _bob_frame(2)]
    aligned, _ = align_frames(frames, canvas_width=16, canvas_height=16, pivot_x=8, pivot_y=14, align="none")
    assert alpha_bbox(aligned[0])[1] == 5
    assert alpha_bbox(aligned[1])[1] == 7


def test_align_refuses_silent_clipping():
    frame = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rectangle((4, 4, 27, 27), fill=(80, 140, 90, 255))
    with pytest.raises(ValueError, match="clipped"):
        align_frames([frame], canvas_width=16, canvas_height=16, pivot_x=8, pivot_y=14)
    aligned, report = align_frames(
        [frame], canvas_width=16, canvas_height=16, pivot_x=8, pivot_y=14, allow_clip=True
    )
    assert aligned[0].size == (16, 16)
    assert report["clip_warnings"] == [0]


def test_validate_animation_pass():
    frames = [_subtle_frame(0), _subtle_frame(1), _subtle_frame(2), _subtle_frame(3)]
    report = validate_animation(
        frames,
        expected_count=4,
        expected_size=(16, 16),
        pivot=(8, 14),
        durations=[100, 100, 100, 100],
    )
    assert report["status"] == "PASS"
    assert report["critical_failures"] == []
    assert report["warnings"] == []


def test_validate_animation_count_mismatch_fails():
    report = validate_animation([_bob_frame(0)], expected_count=4)
    assert report["status"] == "FAIL"
    assert "frame_count" in report["critical_failures"]


def test_validate_animation_empty_frame_fails():
    empty = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    report = validate_animation([_bob_frame(0), empty], expected_count=2)
    assert report["status"] == "FAIL"
    assert "empty_frames" in report["critical_failures"]


def test_validate_animation_duplicate_frames_warn():
    frame = _bob_frame(0)
    report = validate_animation([frame, frame.copy()], expected_count=2)
    assert report["status"] == "WARN"
    assert "duplicate_frames" in report["warnings"]


def test_validate_animation_bad_durations_fail():
    frames = [_bob_frame(0), _bob_frame(1)]
    report = validate_animation(frames, durations=[100])
    assert report["status"] == "FAIL"
    assert "durations" in report["critical_failures"]


def test_validate_animation_pivot_bounds_fail():
    report = validate_animation([_bob_frame(0)], pivot=(99, 99))
    assert report["status"] == "FAIL"
    assert "pivot" in report["critical_failures"]


def test_make_preview_gif_and_webp(tmp_path):
    frames = [_bob_frame(0), _bob_frame(1)]
    gif = make_preview(frames, tmp_path / "preview.gif", durations=[100, 100], background="checker")
    with Image.open(gif) as opened:
        assert opened.n_frames == 2
    webp = make_preview(frames, tmp_path / "preview.webp", durations=[100, 100], background="transparent")
    with Image.open(webp) as opened:
        assert opened.n_frames == 2
    with pytest.raises(FileExistsError):
        make_preview(frames, gif, durations=[100, 100])


def test_make_preview_requires_known_format(tmp_path):
    with pytest.raises(ValueError):
        make_preview([_bob_frame(0)], tmp_path / "preview.bmp")
