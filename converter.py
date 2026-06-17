import argparse
import sys
from pathlib import Path

from PIL import Image

SUPPORTED_FORMATS = {"png", "jpg", "webp"}

FORMAT_TO_PIL = {
    "png": "PNG",
    "jpg": "JPEG",
    "webp": "WEBP",
}

DEFAULT_QUALITY = {
    "png": None,
    "jpg": 85,
    "webp": 80,
}


def _validate_format(fmt: str) -> str:
    fmt = fmt.lower().strip(".")
    if fmt == "jpeg":
        fmt = "jpg"
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format '{fmt}', supported: {sorted(SUPPORTED_FORMATS)}"
        )
    return fmt


def _has_transparency(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA", "PA"):
        return True
    if img.mode == "P" and img.info.get("transparency") is not None:
        return True
    return False


def _prepare_image(img: Image.Image, target_fmt: str) -> Image.Image:
    if target_fmt == "jpg":
        if _has_transparency(img):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            return background
        if img.mode != "RGB":
            return img.convert("RGB")
    if target_fmt == "png" and img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        return img.convert("RGBA")
    if target_fmt == "webp" and img.mode not in ("RGB", "RGBA"):
        return img.convert("RGBA")
    return img


def convert_image(
    input_path: str | Path,
    output_path: str | Path | None = None,
    target_format: str = "png",
    quality: int | None = None,
) -> Path:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    target_fmt = _validate_format(target_format)

    if output_path is None:
        output_path = input_path.with_suffix(f".{target_fmt}")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        img = _prepare_image(img, target_fmt)

        save_kwargs: dict = {"format": FORMAT_TO_PIL[target_fmt]}

        if target_fmt in ("jpg", "webp"):
            q = quality if quality is not None else DEFAULT_QUALITY[target_fmt]
            if q is not None:
                save_kwargs["quality"] = max(1, min(100, q))

        if target_fmt == "png":
            save_kwargs["optimize"] = True

        if target_fmt == "jpg":
            save_kwargs["subsampling"] = 0

        img.save(str(output_path), **save_kwargs)

    return output_path


def batch_convert(
    input_dir: str | Path,
    target_format: str,
    quality: int | None = None,
    output_dir: str | Path | None = None,
    recursive: bool = False,
) -> list[Path]:
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {input_dir}")

    target_fmt = _validate_format(target_format)
    src_exts = {f".{f}" for f in SUPPORTED_FORMATS if f != target_fmt}
    src_exts |= {".jpeg"} if target_fmt != "jpg" else set()

    if output_dir is None:
        output_dir = input_dir / f"converted_{target_fmt}"
    else:
        output_dir = Path(output_dir)

    results: list[Path] = []
    pattern = "**/*" if recursive else "*"
    for f in input_dir.glob(pattern):
        if not f.is_file():
            continue
        if f.suffix.lower() not in src_exts:
            continue
        rel = f.relative_to(input_dir)
        out = output_dir / rel.with_suffix(f".{target_fmt}")
        try:
            p = convert_image(f, out, target_fmt, quality)
            results.append(p)
        except Exception as e:
            print(f"[WARN] Failed to convert {f}: {e}", file=sys.stderr)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Image format converter: PNG <-> JPG <-> WebP"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_single = sub.add_parser("convert", help="Convert a single image")
    p_single.add_argument("input", help="Input image path")
    p_single.add_argument("-o", "--output", help="Output image path (auto-generated if omitted)")
    p_single.add_argument("-f", "--format", required=True, dest="fmt", help="Target format: png/jpg/webp")
    p_single.add_argument("-q", "--quality", type=int, default=None, help="Quality (1-100, for jpg/webp)")

    p_batch = sub.add_parser("batch", help="Batch convert images in a directory")
    p_batch.add_argument("input_dir", help="Input directory")
    p_batch.add_argument("-o", "--output-dir", default=None, help="Output directory")
    p_batch.add_argument("-f", "--format", required=True, dest="fmt", help="Target format: png/jpg/webp")
    p_batch.add_argument("-q", "--quality", type=int, default=None, help="Quality (1-100, for jpg/webp)")
    p_batch.add_argument("-r", "--recursive", action="store_true", help="Recurse into subdirectories")

    args = parser.parse_args()

    if args.command == "convert":
        out = convert_image(args.input, args.output, args.fmt, args.quality)
        print(f"Converted -> {out}")
    elif args.command == "batch":
        results = batch_convert(
            args.input_dir, args.fmt, args.quality, args.output_dir, args.recursive
        )
        print(f"Converted {len(results)} file(s)")
        for r in results:
            print(f"  {r}")


if __name__ == "__main__":
    main()
