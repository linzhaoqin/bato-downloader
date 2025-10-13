import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse


def install_and_import(package: str, import_name: Optional[str] = None) -> None:
    """Ensure a dependency is available before continuing."""
    module = import_name or package
    try:
        __import__(module)
    except ImportError:
        print(f"{package} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"{package} installed successfully.")
            __import__(module)
        except Exception as exc:  # pragma: no cover - installation errors bubble up
            print(f"Failed to install {package}. Please install it manually using:", file=sys.stderr)
            print(f"  python -m pip install {package}", file=sys.stderr)
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


install_and_import("requests")
install_and_import("beautifulsoup4", "bs4")
install_and_import("Pillow", "PIL")
install_and_import("cloudscraper")

import requests
import cloudscraper
from bs4 import BeautifulSoup
from PIL import Image
from parsers import ALL_PARSERS


class DownloadError(Exception):
    """Raised when a download cannot be completed."""


def fetch_soup(scraper: cloudscraper.CloudScraper, url: str) -> BeautifulSoup:
    response = scraper.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def choose_parser(soup: BeautifulSoup, url: str) -> Tuple[object, dict]:
    for parser in ALL_PARSERS:
        if parser.can_parse(soup, url):
            parsed = parser.parse(soup, url)
            if parsed:
                return parser, parsed
    raise DownloadError("No suitable parser found for this URL.")


def prepare_download_dir(title: str, chapter: str, base_dir: Optional[str]) -> Path:
    if base_dir:
        root = Path(base_dir).expanduser()
    else:
        root = Path.home() / "Downloads"
    target_dir = root / f"{title}_{chapter}"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def resolve_extension(response: requests.Response, fallback_index: int) -> str:
    parsed_url = urlparse(response.url)
    name, ext = os.path.splitext(os.path.basename(parsed_url.path))
    if ext:
        return ext
    content_type = response.headers.get("content-type", "")
    match = re.search(r"image/([\w.+-]+)", content_type)
    if match:
        return f".{match.group(1)}"
    return ".jpg" if fallback_index == 1 else f".jpg"


def download_images(
    scraper: cloudscraper.CloudScraper,
    image_urls: Iterable[str],
    target_dir: Path,
    quiet: bool,
) -> Iterable[Path]:
    saved_files = []
    total = len(image_urls) if hasattr(image_urls, "__len__") else None
    for index, image_url in enumerate(image_urls, start=1):
        try:
            response = scraper.get(image_url)
            response.raise_for_status()
        except requests.RequestException as exc:
            if not quiet:
                print(f"[WARN] Failed to download {image_url}: {exc}", file=sys.stderr)
            continue
        extension = resolve_extension(response, index)
        file_path = target_dir / f"{index:03d}{extension}"
        file_path.write_bytes(response.content)
        saved_files.append(file_path)
        if not quiet:
            status = f"{index}/{total}" if total else f"{index}"
            print(f"[INFO] Downloaded image {status}")
    return saved_files


def create_pdf(image_files: Iterable[Path], pdf_path: Path) -> Path:
    images = []
    for path in image_files:
        with Image.open(path) as img:
            images.append(img.convert("RGB"))
    if not images:
        raise DownloadError("No images available to create PDF.")
    first, *rest = images
    first.save(pdf_path, "PDF", resolution=100.0, save_all=True, append_images=rest)
    for image in images:
        image.close()
    return pdf_path


def download_chapter(
    url: str,
    output_dir: Optional[str] = None,
    create_pdf_bundle: bool = True,
    quiet: bool = False,
) -> dict:
    scraper = cloudscraper.create_scraper()
    if not quiet:
        print(f"[INFO] Fetching chapter page: {url}")
    soup = fetch_soup(scraper, url)
    parser, parsed = choose_parser(soup, url)
    if not quiet:
        print(f"[INFO] Using parser: {parser.get_name()}")

    title = parsed["title"]
    chapter = parsed["chapter"]
    images = parsed["image_urls"]
    if not images:
        raise DownloadError("Parser returned no image URLs.")

    download_dir = prepare_download_dir(title, chapter, output_dir)
    if not quiet:
        print(f"[INFO] Saving files under: {download_dir}")

    saved_images = list(download_images(scraper, images, download_dir, quiet))
    if not saved_images:
        raise DownloadError("No images were downloaded successfully.")

    pdf_path = None
    if create_pdf_bundle:
        pdf_path = create_pdf(saved_images, download_dir / f"{title}_{chapter}.pdf")
        if not quiet:
            print(f"[INFO] Created PDF: {pdf_path}")

    return {
        "title": title,
        "chapter": chapter,
        "parser": parser.get_name(),
        "download_dir": download_dir,
        "image_paths": saved_images,
        "pdf_path": pdf_path,
    }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a manga chapter and optionally bundle it into a PDF."
    )
    parser.add_argument("url", help="Manga chapter URL to download.")
    parser.add_argument(
        "-o",
        "--output-dir",
        help="Directory to store downloads (default: ~/Downloads)."
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Download images only, do not generate a PDF bundle.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational output.",
    )
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        result = download_chapter(
            args.url,
            output_dir=args.output_dir,
            create_pdf_bundle=not args.skip_pdf,
            quiet=args.quiet,
        )
    except DownloadError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"[ERROR] Network request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - unexpected failure path
        print(f"[ERROR] Unexpected error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print()
        print(f"Title: {result['title']}")
        print(f"Chapter: {result['chapter']}")
        print(f"Parser: {result['parser']}")
        print(f"Images saved to: {result['download_dir']}")
        pdf_report = result['pdf_path'] if result['pdf_path'] else "PDF creation skipped"
        print(f"PDF: {pdf_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
