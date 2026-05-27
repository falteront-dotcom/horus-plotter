"""Shared pytest fixtures for horus-plotter test suite."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from core.paths import Path, Drawing


# ─── Drawing fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def simple_drawing() -> Drawing:
    """A simple drawing with two paths for basic tests."""
    return Drawing([
        Path([(0, 0), (10, 0), (10, 10)]),
        Path([(20, 0), (30, 0)]),
    ])


@pytest.fixture
def empty_drawing() -> Drawing:
    """An empty drawing with no paths."""
    return Drawing()


@pytest.fixture
def single_path_drawing() -> Drawing:
    """A drawing with a single straight line."""
    return Drawing([Path([(0, 0), (10, 0)])])


# ─── Grid fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def black_grid() -> list[list[float]]:
    """A 20x15 grid of all black (brightness 0)."""
    return [[0.0] * 20 for _ in range(15)]


@pytest.fixture
def white_grid() -> list[list[float]]:
    """A 20x15 grid of all white (brightness 1)."""
    return [[1.0] * 20 for _ in range(15)]


@pytest.fixture
def gradient_grid() -> list[list[float]]:
    """A 20x15 grid with horizontal gradient (left black, right white)."""
    return [[x / 20 for x in range(20)] for _ in range(15)]


@pytest.fixture
def circle_grid() -> list[list[float]]:
    """A 20x15 grid with circular gradient."""
    cx, cy = 10, 7.5
    max_dist = (cx**2 + cy**2) ** 0.5
    grid = []
    for y in range(15):
        row = []
        for x in range(20):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            row.append(min(1.0, dist / max_dist))
        grid.append(row)
    return grid


# ─── Image fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def black_image() -> Image.Image:
    """A 100x100 black PIL image."""
    return Image.new("L", (100, 100), 0)


@pytest.fixture
def white_image() -> Image.Image:
    """A 100x100 white PIL image."""
    return Image.new("L", (100, 100), 255)


@pytest.fixture
def gradient_image() -> Image.Image:
    """A 100x100 image with a dark rectangle on white background."""
    img = Image.new("L", (100, 100), 255)
    draw = ImageDraw.Draw(img)
    draw.rectangle([25, 25, 75, 75], fill=0)
    return img


@pytest.fixture
def dark_background_image() -> Image.Image:
    """A dark image with a light square for auto-invert tests."""
    img = Image.new("L", (100, 100), 30)
    draw = ImageDraw.Draw(img)
    draw.rectangle([30, 30, 70, 70], fill=230)
    return img
