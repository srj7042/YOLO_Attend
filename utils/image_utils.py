import os
import uuid
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def is_allowed_image(filename):
    """Check if file extension is an allowed image type."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS

def save_and_optimize_student_photo(file_storage, target_dir, max_dim=1280, thumb_dim=(160, 160)):
    """
    Saves an uploaded photo with:
    1. EXIF auto-rotation (fixes sideways/upside-down phone camera uploads).
    2. High-res optimized WebP conversion (max 1280px on longest edge, 85% quality).
    3. Fast-loading WebP avatar thumbnail (160x160 px, ~3KB).

    Returns:
        tuple: (saved_image_path, thumbnail_path, unique_filename)
    """
    os.makedirs(target_dir, exist_ok=True)

    orig_name = secure_filename(file_storage.filename) or 'photo.jpg'
    name_root = orig_name.rsplit('.', 1)[0] if '.' in orig_name else orig_name
    unique_prefix = uuid.uuid4().hex[:8]

    optimized_filename = f"{unique_prefix}_{name_root}.webp"
    thumb_filename = f"thumb_{unique_prefix}_{name_root}.webp"

    optimized_path = os.path.join(target_dir, optimized_filename)
    thumb_path = os.path.join(target_dir, thumb_filename)

    # Open image with Pillow and fix smartphone orientation
    image = Image.open(file_storage)
    image = ImageOps.exif_transpose(image)

    # Convert to RGB (handles RGBA / Palette / Grayscale modes)
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # Downscale high-res images if exceeds max_dim while maintaining aspect ratio
    w, h = image.size
    if max(w, h) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    # Save optimized main image
    image.save(optimized_path, format='WEBP', quality=85, method=4)

    # Generate and save thumbnail with center crop to 1:1 square
    thumb_img = ImageOps.fit(image, thumb_dim, method=Image.Resampling.LANCZOS)
    thumb_img.save(thumb_path, format='WEBP', quality=80, method=4)

    return optimized_path, thumb_path, optimized_filename


def get_or_create_thumbnail(image_path, thumb_dim=(160, 160)):
    """
    Returns thumbnail path for an image.
    If thumbnail does not exist on disk, creates and caches it.
    """
    if not image_path or not os.path.exists(image_path):
        return None

    dirname, filename = os.path.split(image_path)
    if filename.startswith('thumb_'):
        return image_path

    thumb_filename = f"thumb_{filename.rsplit('.', 1)[0]}.webp"
    thumb_path = os.path.join(dirname, thumb_filename)

    if os.path.exists(thumb_path):
        return thumb_path

    try:
        image = Image.open(image_path)
        image = ImageOps.exif_transpose(image)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        thumb_img = ImageOps.fit(image, thumb_dim, method=Image.Resampling.LANCZOS)
        thumb_img.save(thumb_path, format='WEBP', quality=80, method=4)
        return thumb_path
    except Exception as e:
        print(f"[WARN] Failed to generate thumbnail for {image_path}: {e}")
        return image_path
