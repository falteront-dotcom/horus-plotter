"""Tests for custom exceptions."""

from __future__ import annotations

import pytest

from core.exceptions import (
    ConfigError,
    ConverterError,
    EmptyDocumentError,
    ImageLoadError,
    PlotterError,
    UnsupportedFormatError,
)


class TestPlotterError:
    def test_base_error_message(self) -> None:
        err = PlotterError("something went wrong")
        assert str(err) == "something went wrong"
        assert err.message == "something went wrong"


class TestImageLoadError:
    def test_error_message(self) -> None:
        err = ImageLoadError("/path/to/image.png", "file not found")
        assert err.path == "/path/to/image.png"
        assert err.reason == "file not found"
        assert "image.png" in str(err)
        assert "file not found" in str(err)


class TestUnsupportedFormatError:
    def test_error_message(self) -> None:
        err = UnsupportedFormatError("file.xyz", ".xyz")
        assert err.ext == ".xyz"
        assert ".xyz" in str(err)

    def test_is_image_load_error(self) -> None:
        err = UnsupportedFormatError("file.xyz", ".xyz")
        assert isinstance(err, ImageLoadError)


class TestEmptyDocumentError:
    def test_error_message(self) -> None:
        err = EmptyDocumentError("empty.pdf")
        assert "empty.pdf" in str(err)
        assert "no renderable content" in str(err)


class TestConverterError:
    def test_error_message(self) -> None:
        err = ConverterError("halftone", "grid is empty")
        assert err.style == "halftone"
        assert "halftone" in str(err)
        assert "grid is empty" in str(err)


class TestConfigError:
    def test_error_message(self) -> None:
        err = ConfigError("speed", -100, "positive integer")
        assert err.field == "speed"
        assert err.value == -100
        assert "speed" in str(err)
        assert "-100" in str(err)
