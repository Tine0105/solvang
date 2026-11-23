"""Image optimization utility: WebP/AVIF/JPG conversion, responsive srcset, thumbnails, blur check, and pHash."""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
from typing import Any
from PIL import Image, ImageFilter, ImageOps, ImageStat


def compute_dhash(image: Image.Image, hash_size: int = 8) -> str:
    """Compute a 64-bit difference hash (dHash/pHash) using Pillow for duplicate detection."""
    gray = image.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    bits = []
    for row in range(hash_size):
        offset = row * (hash_size + 1)
        for col in range(hash_size):
            bits.append('1' if pixels[offset + col] > pixels[offset + col + 1] else '0')
    return hex(int(''.join(bits), 2))[2:].zfill(16)


def compute_laplacian_variance(image: Image.Image) -> float:
    """Compute 3x3 Laplacian variance on a 640px grayscale version to detect blurry images."""
    gray = image.convert('L')
    if gray.width > 640:
        ratio = 640 / gray.width
        gray = gray.resize((640, max(1, int(gray.height * ratio))), Image.Resampling.BILINEAR)
    lap_kernel = ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=128)
    edges = gray.filter(lap_kernel)
    stat = ImageStat.Stat(edges)
    return float(stat.var[0])


def _save_variant(img: Image.Image, out_path: Path, fmt: str, quality: int) -> None:
    kwargs: dict[str, Any] = {'optimize': True}
    if fmt in ('JPEG', 'WEBP', 'AVIF'):
        kwargs['quality'] = quality
    if fmt == 'WEBP':
        kwargs['method'] = 4
    img.save(out_path, format=fmt, **kwargs)


def optimize_image(
    src_path: str | Path,
    dest_dir: str | Path,
    stem: str,
    widths: tuple[int, ...] = (1920, 1280, 768),
    thumb_width: int = 640,
    return_thumb_bytes: bool = False,
) -> dict[str, Any]:
    """Optimize an image into WebP, optional AVIF, JPG fallback, and thumbnail variants."""
    src_path = Path(src_path)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    raw_bytes = src_path.read_bytes()
    sha256_hex = hashlib.sha256(raw_bytes).hexdigest()

    with Image.open(io.BytesIO(raw_bytes)) as raw:
        img = ImageOps.exif_transpose(raw).convert('RGB')
        dhash = compute_dhash(img)
        blur_var = compute_laplacian_variance(img)
        orig_w, orig_h = img.size

        main_img = img.copy()
        if main_img.width > 2400:
            ratio = 2400 / main_img.width
            main_img = main_img.resize((2400, int(main_img.height * ratio)), Image.Resampling.LANCZOS)

        jpg_main = dest_dir / f'{stem}.jpg'
        webp_main = dest_dir / f'{stem}.webp'
        _save_variant(main_img, jpg_main, 'JPEG', 86)
        _save_variant(main_img, webp_main, 'WEBP', 84)

        avif_created = False
        try:
            avif_main = dest_dir / f'{stem}.avif'
            _save_variant(main_img, avif_main, 'AVIF', 62)
            avif_created = True
        except Exception:
            pass

        srcset_webp = []
        for w in widths:
            if main_img.width >= w:
                ratio = w / main_img.width
                resized = main_img.resize((w, int(main_img.height * ratio)), Image.Resampling.LANCZOS)
                variant = dest_dir / f'{stem}-{w}w.webp'
                _save_variant(resized, variant, 'WEBP', 82)
                srcset_webp.append((w, variant.name))

        thumb_ratio = thumb_width / main_img.width
        thumb_img = main_img.resize((thumb_width, int(main_img.height * thumb_ratio)), Image.Resampling.LANCZOS)
        thumb_webp = dest_dir / f'{stem}-thumb.webp'
        _save_variant(thumb_img, thumb_webp, 'WEBP', 80)

        thumb_bytes = thumb_webp.read_bytes() if return_thumb_bytes else None

    return {
        'sha256': sha256_hex,
        'dhash': dhash,
        'blur_variance': round(blur_var, 2),
        'orig_size': (orig_w, orig_h),
        'file_size': webp_main.stat().st_size,
        'jpg': jpg_main.name,
        'webp': webp_main.name,
        'avif': f'{stem}.avif' if avif_created else None,
        'thumb': thumb_webp.name,
        'thumb_bytes': thumb_bytes,
        'srcset': srcset_webp,
    }


def main():
    parser = argparse.ArgumentParser(description='Optimize car images into WebP/JPG/thumbnails.')
    parser.add_argument('input_dir', help='Directory containing raw images')
    parser.add_argument('--out', help='Output directory (defaults to input_dir)')
    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.out) if args.out else in_dir
    exts = {'.jpg', '.jpeg', '.png', '.webp'}
    count = 0
    for f in sorted(in_dir.rglob('*')):
        if f.suffix.lower() in exts and '-thumb' not in f.stem and not any(f.stem.endswith(f'-{w}w') for w in (1920, 1280, 768)):
            optimize_image(f, out_dir / f.relative_to(in_dir).parent, f.stem)
            count += 1
    print(f'Optimized {count} images.')


if __name__ == '__main__':
    main()
