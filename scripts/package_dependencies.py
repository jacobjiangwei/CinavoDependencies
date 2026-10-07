#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import sys
import tarfile
import tempfile


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def restore_prepared_pods(archive, payload, root, spec):
    lock = json.loads((root / "prepared-pods.json").read_text())
    if lock["format"] != 1 or digest(archive) != lock["sha256"]:
        raise ValueError("Prepared CocoaPods archive does not match its pinned SHA-256.")
    if sys.version_info < (3, 12):
        raise RuntimeError("Restoring prepared CocoaPods requires Python 3.12 or newer.")
    with tarfile.open(archive, "r:gz") as package:
        with package.extractfile("dependency-manifest.json") as source:
            manifest = json.load(source)
        for key in ("podfile_sha256", "podfile_lock_sha256"):
            if manifest[key] != lock[key]:
                raise ValueError(f"Prepared CocoaPods {key} does not match its lock.")
        for key in ("vlckit", "mobilevlckit", "cocoapods"):
            if manifest["dependencies"][key] != spec[key]:
                raise ValueError(f"Regenerate the prepared CocoaPods snapshot for changed {key}.")
        members = [
            member for member in package.getmembers()
            if member.name == "Pods" or member.name.startswith("Pods/")
        ]
        package.extractall(payload, members=members, filter="data")
    for relative, expected in manifest["files"].items():
        if not relative.startswith("Pods/"):
            continue
        path = payload / relative
        if "symlink" in expected:
            if not path.is_symlink() or str(path.readlink()) != expected["symlink"]:
                raise ValueError(f"Prepared CocoaPods link validation failed: {relative}")
        elif not path.is_file() or path.stat().st_size != expected["size"] or digest(path) != expected["sha256"]:
            raise ValueError(f"Prepared CocoaPods file validation failed: {relative}")
    if digest(payload / "Pods/Manifest.lock") != lock["podfile_lock_sha256"]:
        raise ValueError("Prepared CocoaPods Manifest.lock does not match the consumer lockfile.")
    return lock["podfile_sha256"], lock["podfile_lock_sha256"]


def main():
    parser = argparse.ArgumentParser()
    pods = parser.add_mutually_exclusive_group(required=True)
    pods.add_argument("--cinavo", type=Path)
    pods.add_argument("--pods-archive", type=Path)
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
    if args.cinavo:
        lockfile = args.cinavo / "Podfile.lock"
        if lockfile.read_bytes() != (args.cinavo / "Pods/Manifest.lock").read_bytes():
            raise ValueError("Regenerate locked CocoaPods dependencies before packaging.")
        lock_text = lockfile.read_text()
        for pod, key in [("VLCKit", "vlckit"), ("MobileVLCKit", "mobilevlckit")]:
            if f"- {pod} ({spec[key]['version']})" not in lock_text:
                raise ValueError(f"{pod} version does not match dependencies.json.")
    archive = output / f"cinavo-dependencies-{args.version}.tar.gz"
    if archive.exists():
        raise FileExistsError("Release versions are immutable; choose a new version.")
    with tempfile.TemporaryDirectory(prefix="payload-", dir=output) as temporary:
        payload = Path(temporary)
        if args.pods_archive:
            podfile_sha256, podfile_lock_sha256 = restore_prepared_pods(
                args.pods_archive, payload, root, spec
            )
        else:
            shutil.copytree(
                args.cinavo / "Pods", payload / "Pods", symlinks=True,
                ignore=shutil.ignore_patterns("dSYMs", "*.dSYM", "xcuserdata", ".DS_Store"),
            )
            podfile_sha256 = digest(args.cinavo / "Podfile")
            podfile_lock_sha256 = digest(lockfile)
        shutil.copytree(
            ffmpeg, payload / "Vendor/FFmpeg",
            ignore=shutil.ignore_patterns("*-config.log"),
        )
        # Symbols are not distributed with this build dependency bundle.
        for path in (payload / "Pods").glob("*/*.xcframework/Info.plist"):
            info = plistlib.loads(path.read_bytes())
            for library in info["AvailableLibraries"]:
                library.pop("DebugSymbolsPath", None)
            path.write_bytes(plistlib.dumps(info))
        files = {}
        for path in sorted(payload.rglob("*")):
            relative = str(path.relative_to(payload))
            if path.is_symlink():
                files[relative] = {"symlink": str(path.readlink())}
            elif path.is_file():
                files[relative] = {"sha256": digest(path), "size": path.stat().st_size}
        manifest = {
            "format": 1,
            "version": args.version,
            "dependencies": spec,
            "ffmpeg_build": build_info,
            "podfile_sha256": podfile_sha256,
            "podfile_lock_sha256": podfile_lock_sha256,
            "payload_uncompressed_bytes": sum(value.get("size", 0) for value in files.values()),
            "files": files,
        }
        (payload / "dependency-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        with tarfile.open(archive, "w:gz", compresslevel=6) as package:
            for name in ["Pods", "Vendor", "dependency-manifest.json"]:
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
