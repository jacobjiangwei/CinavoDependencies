#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="7.1.3"
SHA256="f0bf043299db9e3caacb435a712fc541fbb07df613c4b893e8b77e67baf3adbe"
BUILD_ROOT="${ROOT}/.build/ffmpeg"
OUTPUT="${ROOT}/dist/ffmpeg"
ARCHIVE="${BUILD_ROOT}/ffmpeg-${VERSION}.tar.xz"
JOBS="${JOBS:-4}"
LIBRARIES=(avformat avcodec avutil swresample swscale)

case "$JOBS" in
  1|2|3|4|5|6|7|8) ;;
  *) echo "JOBS must be an integer between 1 and 8." >&2; exit 1 ;;
esac
mkdir -p "$BUILD_ROOT" "$OUTPUT"
if [[ ! -f "$ARCHIVE" ]]; then
  if [[ -n "${FFMPEG_SOURCE_ARCHIVE:-}" ]]; then
    cp "$FFMPEG_SOURCE_ARCHIVE" "$ARCHIVE"
  else
    curl --fail --location --show-error --retry 3 --connect-timeout 20 \
      "https://ffmpeg.org/releases/ffmpeg-${VERSION}.tar.xz" -o "$ARCHIVE"
  fi
fi
printf '%s  %s\n' "$SHA256" "$ARCHIVE" | shasum -a 256 -c -

COMMON_FLAGS=(
  --enable-static
  --disable-shared
  --enable-pic
  --disable-doc
  --disable-programs
  --disable-avdevice
  --disable-devices
  --enable-network
  --disable-autodetect
  --disable-encoders
  --disable-muxers
  --disable-filters
  --disable-bsfs
  --disable-postproc
  --disable-asm
  --disable-gpl
  --disable-nonfree
  --enable-demuxers
  --enable-decoders
  --enable-parsers
  --enable-protocol=file,http,tcp
  --enable-swresample
  --enable-swscale
  --enable-muxer=pcm_f32le,srt,ass,webvtt
  --enable-encoder=pcm_f32le,srt,ass,webvtt
  --enable-filter=aresample,aformat,anull
  --enable-cross-compile
)

for platform in macosx iphoneos iphonesimulator; do
  sdk="$(xcrun --sdk "$platform" --show-sdk-path)"
  compiler="$(xcrun --sdk "$platform" --find clang)"
  case "$platform" in
    macosx) minimum="-mmacosx-version-min=26.0" ;;
    iphoneos) minimum="-mios-version-min=26.0" ;;
    iphonesimulator) minimum="-mios-simulator-version-min=26.0" ;;
  esac
  source_root="${BUILD_ROOT}/${platform}"
  source="${source_root}/ffmpeg-${VERSION}"
  prefix="${source_root}/install"
  mkdir -p "$source_root"
  if [[ ! -d "$source" ]]; then
    tar -xf "$ARCHIVE" -C "$source_root"
  fi
  echo "Building FFmpeg ${VERSION}: ${platform}, arm64, ${minimum}, ${JOBS} jobs"
  (
    cd "$source"
    if [[ -f ffbuild/config.mak ]]; then make distclean; fi
    ./configure \
      --prefix="$prefix" --target-os=darwin --arch=arm64 \
      --cc="$compiler" --sysroot="$sdk" \
      "${COMMON_FLAGS[@]}" \
      --extra-cflags="-arch arm64 -isysroot ${sdk} ${minimum}" \
      --extra-ldflags="-arch arm64 -isysroot ${sdk} ${minimum}"
    make -j"$JOBS"
    make install
    cp ffbuild/config.log "${OUTPUT}/${platform}-config.log"
  )
  mkdir -p "${OUTPUT}/${platform}/lib"
  archives=()
  for library in "${LIBRARIES[@]}"; do
    destination="${OUTPUT}/${platform}/lib/lib${library}.a"
    cp "${prefix}/lib/lib${library}.a" "$destination"
    lipo -verify_arch arm64 "$destination"
    archives+=("$destination")
  done
  ruby "${ROOT}/scripts/normalize_static_archive_members.rb" "${archives[@]}"
  if [[ "$platform" == "macosx" ]]; then
    mkdir -p "${OUTPUT}/include" "${OUTPUT}/licenses"
    cp -R "${prefix}/include/." "${OUTPUT}/include/"
    cp "${source}/COPYING.LGPLv2.1" "${OUTPUT}/licenses/"
  fi
done

python3 - "$ROOT" "$OUTPUT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path
root, output = map(Path, sys.argv[1:])
spec = json.loads((root / "dependencies.json").read_text())
info = {
    "format": 1,
    "ffmpeg": spec["ffmpeg"],
    "xcode": subprocess.check_output(["xcodebuild", "-version"], text=True).strip(),
    "platforms": ["macosx", "iphoneos", "iphonesimulator"],
    "linkage": "static",
    "gpl_enabled": False,
    "nonfree_enabled": False,
}
(output / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")
PY
echo "Verified FFmpeg output: $OUTPUT"
