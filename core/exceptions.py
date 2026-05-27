"""Custom exceptions for the horus-plotter package."""

from __future__ import annotations


class PlotterError(Exception):
    """Base exception for all plotter-related errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ImageLoadError(PlotterError):
    """Raised when an image cannot be loaded or converted."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load image '{path}': {reason}")


class UnsupportedFormatError(ImageLoadError):
    """Raised when an unsupported file format is encountered."""

    def __init__(self, path: str, ext: str) -> None:
        self.ext = ext
        super().__init__(path, f"Unsupported file format '{ext}'")


class EmptyDocumentError(ImageLoadError):
    """Raised when a document (PDF, DOCX) contains no renderable content."""

    def __init__(self, path: str) -> None:
        super().__init__(path, "Document contains no renderable content")


class ConverterError(PlotterError):
    """Raised when a converter fails to process a grid."""

    def __init__(self, style: str, reason: str) -> None:
        self.style = style
        super().__init__(f"Converter '{style}' failed: {reason}")


class ConfigError(PlotterError):
    """Raised when plot configuration is invalid."""

    def __init__(self, field: str, value: object, expected: str) -> None:
        self.field = field
        self.value = value
        super().__init__(
            f"Invalid config for '{field}': got {value!r}, expected {expected}"
        )
