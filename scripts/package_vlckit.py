#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", args.version):
        parser.error("Use a new immutable runtime release version.")
    root = Path(__file__).resolve().parents[1]
    spec = json.loads((root / "vlckit.json").read_text())
    if digest(args.archive) != spec["source_sha256"]:
        raise ValueError("Official VLCKit archive SHA-256 does not match the pinned source.")
    output = root / "dist"
    output.mkdir(exist_ok=True)
    archive = output / f"cinavo-vlckit-{spec['version']}-{args.version}.zip"
    if archive.exists():
        raise FileExistsError("Runtime Release versions are immutable.")
    with tempfile.TemporaryDirectory(prefix="vlckit-", dir=output) as temporary:
        temporary = Path(temporary)
        source = temporary / "source"
        subprocess.run(["/usr/bin/ditto", "-xk", str(args.archive.resolve()), str(source)], check=True)
        frameworks = list(source.rglob("VLCKit.xcframework"))
        if len(frameworks) != 1:
            raise ValueError("Official archive must contain exactly one VLCKit.xcframework.")
        framework = frameworks[0]
        info = plistlib.loads((framework / "Info.plist").read_bytes())
        libraries = [
            library for library in info["AvailableLibraries"]
            if library["SupportedPlatform"] in ("macos", "ios", "tvos", "xros")
            and library.get("SupportedPlatformVariant", "") in ("", "simulator")
            and "arm64" in library["SupportedArchitectures"]
        ]
        expected = {
            ("macos", ""), ("ios", ""), ("ios", "simulator"),
            ("tvos", ""), ("tvos", "simulator"), ("xros", ""), ("xros", "simulator"),
        }
        if {(library["SupportedPlatform"], library.get("SupportedPlatformVariant", "")) for library in libraries} != expected:
            raise ValueError("VLCKit must contain all seven arm64 SDK variants.")
        payload = temporary / "runtime"
        target = payload / "VLCKit.xcframework"
        target.mkdir(parents=True)
        for library in libraries:
            identifier = library["LibraryIdentifier"]
            if Path(identifier).name != identifier:
                raise ValueError("Unexpected XCFramework library identifier.")
            shutil.copytree(
                framework / identifier, target / identifier, symlinks=True,
                ignore=shutil.ignore_patterns("dSYMs", "*.dSYM", ".DS_Store"),
            )
            library.pop("DebugSymbolsPath", None)
            binary = target / identifier / library["LibraryPath"] / "VLCKit"
            header = binary.parent / "Headers/VLCKit.h"
            if not binary.is_file() or not header.is_file():
                raise ValueError(f"Missing VLCKit binary or umbrella header: {identifier}")
            subprocess.run(["xcrun", "lipo", str(binary), "-verify_arch", "arm64"], check=True)
        info["AvailableLibraries"] = libraries
        (target / "Info.plist").write_bytes(plistlib.dumps(info))
        notices = list(source.rglob("COPYING.txt"))
        if not notices:
            raise ValueError("Official VLCKit license notice is missing.")
        shutil.copy2(notices[0], payload / "COPYING.txt")
        files = {}
        for path in sorted(payload.rglob("*")):
            relative = str(path.relative_to(payload))
            if path.is_symlink():
                files[relative] = {"symlink": str(path.readlink())}
            elif path.is_file():
                files[relative] = {"size": path.stat().st_size, "sha256": digest(path)}
        manifest = {
            "format": 1, "component": "vlckit", "version": spec["version"],
            "release_version": args.version, "source": spec,
            "payload_uncompressed_bytes": sum(item.get("size", 0) for item in files.values()),
            "files": files,
        }
        (payload / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        subprocess.run(["/usr/bin/ditto", "-c", "-k", str(payload), str(archive)], check=True)
    checksum = digest(archive)
    archive.with_name(archive.name + ".sha256").write_text(f"{checksum}  {archive.name}\n")
    archive.with_name(archive.name + ".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Runtime archive: {archive}")
    print(f"SHA-256: {checksum}")
    print(f"Runtime download: {archive.stat().st_size / 1024**2:.1f} MiB")


if __name__ == "__main__":
    main()
