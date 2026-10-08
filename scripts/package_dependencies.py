#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.version):
        parser.error("Use an immutable release version without path separators.")
    root = Path(__file__).resolve().parents[1]
    output = root / "dist"
    ffmpeg = output / "ffmpeg"
    spec = json.loads((root / "dependencies.json").read_text())
    build_info = json.loads((ffmpeg / "build-info.json").read_text())
    if build_info["ffmpeg"] != spec["ffmpeg"] or build_info["gpl_enabled"] or build_info["nonfree_enabled"]:
        raise ValueError("FFmpeg build provenance does not match the locked LGPL recipe.")
    for platform in ("macosx", "iphoneos", "iphonesimulator"):
        for library in spec["ffmpeg"]["libraries"]:
            path = ffmpeg / platform / "lib" / f"lib{library}.a"
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"Missing compiled FFmpeg archive: {path}")
    archive = output / f"cinavo-ffmpeg-{args.version}.tar.gz"
    if archive.exists():
        raise FileExistsError("Release versions are immutable; choose a new version.")
    with tempfile.TemporaryDirectory(prefix="payload-", dir=output) as temporary:
        payload = Path(temporary)
        shutil.copytree(
            ffmpeg, payload / "Vendor/FFmpeg",
            ignore=shutil.ignore_patterns("*-config.log"),
        )
        files = {}
        for path in sorted(payload.rglob("*")):
            relative = str(path.relative_to(payload))
            if path.is_symlink():
                files[relative] = {"symlink": str(path.readlink())}
            elif path.is_file():
                files[relative] = {"sha256": digest(path), "size": path.stat().st_size}
        manifest = {
            "format": 2,
            "version": args.version,
            "dependencies": spec,
            "ffmpeg_build": build_info,
            "payload_uncompressed_bytes": sum(value.get("size", 0) for value in files.values()),
            "files": files,
        }
        (payload / "dependency-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        with tarfile.open(archive, "w:gz", compresslevel=6) as package:
            for name in ["Vendor", "dependency-manifest.json"]:
                package.add(payload / name, arcname=name)
    checksum = digest(archive)
    (output / f"{archive.name}.sha256").write_text(f"{checksum}  {archive.name}\n")
    (output / f"{archive.name}.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Archive: {archive}")
    print(f"SHA-256: {checksum}")
    print(f"Compressed size: {archive.stat().st_size / 1024 / 1024:.1f} MiB")
    print(f"Runtime payload: {manifest['payload_uncompressed_bytes'] / 1024 / 1024:.1f} MiB")


if __name__ == "__main__":
    main()
