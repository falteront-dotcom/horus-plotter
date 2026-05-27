"""Image preprocessing: brightness, contrast, invert, blur."""

from __future__ import annotations
from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(img: Image.Image,
                     brightness: float = 1.0,
                     contrast: float = 1.0,
                     invert: bool = False,
                     blur: float = 0) -> Image.Image:
    """Apply preprocessing to an image before conversion.

    Args:
        brightness: 1.0 = unchanged, >1 brighter, <1 darker
        contrast: 1.0 = unchanged, >1 more contrast
        invert: flip dark/light regions
        blur: Gaussian blur radius (0 = no blur)
    """
    if invert:
        img = Image.eval(img, lambda x: 255 - x)

    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)

    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)

    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    return img
