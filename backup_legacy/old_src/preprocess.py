import cv2
import numpy as np
from PIL import Image

def fix_orientation(image_path):
    """
    Read image and correct rotation using EXIF orientation data.
    Phone cameras often embed rotation in EXIF but the pixel data is sideways.
    Returns a BGR numpy array with correct orientation.
    """
    # Use Pillow to read and auto-rotate based on EXIF
    pil_img = Image.open(image_path)
    
    exif_rotation_map = {
        3: 180,
        6: 270,
        8: 90,
    }
    
    try:
        exif_data = pil_img._getexif()
        if exif_data:
            orientation = exif_data.get(274)  # Tag 274 = Orientation
            degrees = exif_rotation_map.get(orientation, 0)
            if degrees:
                pil_img = pil_img.rotate(degrees, expand=True)
    except (AttributeError, Exception):
        pass  # No EXIF, keep as-is

    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img


def preprocess_image(image_path):
    """
    Load, auto-rotate, and lightly crop the image to remove camera borders.
    Uses EXIF orientation data to fix sideways/rotated images.
    """
    img = fix_orientation(image_path)
    
    h, w = img.shape[:2]

    # Ensure portrait orientation (height > width); rotate if landscape
    if w > h:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        h, w = img.shape[:2]

    # Light crop — 3% each side to trim black borders without cutting content
    top    = int(h * 0.03)
    bottom = int(h * 0.97)
    left   = int(w * 0.03)
    right  = int(w * 0.97)

    cropped = img[top:bottom, left:right]
    return cropped