# CinavoDependencies

FFmpeg build recipes and independently pinned VLC runtime Release assets for
Cinavo. The consumer resolves unified VLCKit through a CocoaPod specification
that points to the verified runtime mirror. No downloaded binary enters Git.

## FFmpeg

`dependencies.json` pins FFmpeg 7.1.3 and its official source SHA-256.
`scripts/build_ffmpeg.sh` builds five static libraries for each of seven arm64
SDK variants: macOS plus iOS, tvOS and visionOS devices/simulators. The libraries
are avformat, avcodec, avutil, swresample and swscale. Minimum versions are 26.0
on all four platforms. CLI programs, GPL components,
nonfree components and automatically detected external libraries are disabled.

```sh
bash scripts/build_ffmpeg.sh
python3 scripts/package_dependencies.py --version NEW_VERSION
```

`JOBS` defaults to four and accepts 1-8. `FFMPEG_SOURCE_ARCHIVE` can supply a
local source archive, subject to the same mandatory checksum verification.
Build output and source caches stay out of Git and Git LFS.

## GitHub Actions and Releases

Run **Build Apple FFmpeg** with a new immutable version:

```sh
gh workflow run build-dependencies.yml \
  --repo jacobjiangwei/CinavoDependencies --field version=2026.10.08.2
```

The arm64 `macos-26` job verifies and compiles FFmpeg from source for all seven
SDK variants. It neither downloads nor packages CocoaPods or VLC. The built-in workflow
token publishes the Release and is never stored in artifacts.

Each `deps-NEW_VERSION` Release includes:

- `cinavo-ffmpeg-NEW_VERSION.tar.gz`: only `Vendor/FFmpeg/` and its manifest.
- Its SHA-256 sidecar and per-file manifest (format 2).
- The exact corresponding `ffmpeg-7.1.3.tar.xz` source archive.

The consumer pins the asset ID, immutable version and SHA-256 in
`Cinavo/Configuration/Dependencies.lock.json`. Public consumption is anonymous;
private consumption requires a repository-scoped Contents: Read token.
Consumers must verify the checksum and every payload file and must never follow
`latest` or extract the package over `Pods/`.

## Universal VLC runtime

`vlckit.json` pins the official VLCKit 4.0.0a25 distribution and original archive
SHA-256. **Package universal VLC runtime** downloads and verifies that original
archive in GitHub Actions, then preserves the seven required native device/
simulator slices and their headers, framework symlinks and license notice.
Only dSYMs, watchOS and Catalyst slices are omitted. The binary libraries are
neither modified nor recompiled; the trimmed root XCFramework metadata and
per-file manifest describe the exact runtime payload.

```sh
gh workflow run package-vlckit.yml \
  --repo jacobjiangwei/CinavoDependencies --field version=2026.10.08.1
```

The original upstream archive is approximately 880 MiB. Mirroring only runtime
inputs avoids repeatedly downloading its unused debug/platform payload on
every consumer build. CocoaPods still validates the runtime archive SHA-256.
The consumer's local Podspec pins its immutable Release URL and checksum.

The earlier `2026.10.07.1` and `2026.10.07.2` Releases contain combined
CocoaPods/VLC/FFmpeg bundles. They are legacy artifacts, not inputs to current
builds. Existing Releases are not overwritten or automatically deleted.

## Publication and licensing boundaries

Keep application source, generated app projects, app bundles, model weights,
signing material and credentials out of new commits and Releases. Public visibility
includes history and Actions logs, including the legacy combined releases.
Third-party code keeps its upstream license; do not apply a blanket proprietary
or permissive license to these binaries.

FFmpeg LGPL notices accompany its libraries. Each binary Release includes the
exact source archive, with configuration and provenance recorded in the tagged
recipe and manifest. Disabled GPL/nonfree flags apply only to this FFmpeg build,
not to VLC components in legacy artifacts.

This dependency distribution does not settle the application distributor's
attribution, modified-source, static-link relinking or codec-patent obligations.
Legacy VLC bundles retain their COPYING files and acknowledgements, but their
corresponding bundled-library sources and license conditions are not certified
by the wrapper notice alone. See the
[FFmpeg legal checklist](https://ffmpeg.org/legal.html) and
[VideoLAN redistribution guidance](https://www.videolan.org/legal.html).
