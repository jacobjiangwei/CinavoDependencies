# CinavoDependencies

FFmpeg build recipes and versioned Release assets for Cinavo. Only FFmpeg is
delivered here: CocoaPods and VLC stay in the application repository, following
the existing iOS project's vendored-Pods workflow.

## FFmpeg

`dependencies.json` pins FFmpeg 7.1.3 and its official source SHA-256.
`scripts/build_ffmpeg.sh` builds five static libraries for each of arm64 macOS,
iOS devices and iOS simulators: avformat, avcodec, avutil, swresample and swscale.
Minimum versions are macOS 26.0 and iOS 26.0. CLI programs, GPL components,
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
  --repo jacobjiangwei/CinavoDependencies --field version=2026.10.08.1
```

The arm64 `macos-26` job verifies and compiles FFmpeg from source for all three
SDKs. It neither downloads nor packages CocoaPods or VLC. The built-in workflow
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

The earlier `2026.10.07.1` and `2026.10.07.2` Releases contain combined
CocoaPods/VLC/FFmpeg bundles. They are legacy artifacts, not inputs to current
builds. Existing Releases are not overwritten or automatically deleted.

## Publication and licensing boundaries

Keep application source, CocoaPods/VLC, app bundles, model weights, signing
material and credentials out of new commits and Releases. Public visibility
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
