# CinavoDependencies

Private dependency build recipes and versioned Release assets for Cinavo.
No application code, UI, model weights or credentials belong in this repository.
Binaries are Release assets, never Git or Git LFS objects.

## FFmpeg

`dependencies.json` pins FFmpeg 7.1.3 and the SHA-256 of its official source.
`scripts/build_ffmpeg.sh` builds only the five static libraries for arm64 macOS,
iOS devices and iOS simulators. Minimum versions are macOS 26.0 and iOS 26.0.
CLI programs, GPL components and nonfree components are disabled.

```sh
bash scripts/build_ffmpeg.sh
```

`JOBS` defaults to four and accepts 1-8. A local verified source archive can be
provided as `FFMPEG_SOURCE_ARCHIVE`; it receives the same mandatory checksum
validation as a fresh download. Output and source caches are ignored by Git.

## Release bundle

The bundle contains newly built FFmpeg libraries/headers/licenses and the
pinned upstream VLCKit 3.7.3 / MobileVLCKit 3.7.4 runtime frameworks.
VLC frameworks are upstream precompiled CocoaPods artifacts, not claimed to
have been compiled locally. Prepared CocoaPods project, xcconfig and xcfilelist
files are included so Xcode Cloud does not need to install CocoaPods with its
system Ruby. These support files are tied to the consumer's Podfile/lockfile
hashes. Swift dependencies such as WhisperKit remain native SwiftPM packages.

Debug symbols, DerivedData, compiled app bundles and secrets are excluded.
Release consumers must verify the archive SHA-256 and the consumer lockfile
hashes before extraction. Private downloads require a repository-scoped
read-only token configured as an Xcode Cloud secret; no token is stored here.

FFmpeg LGPL notices and VLC wrapper license notices accompany the binaries.
Exact upstream source URLs and checksums are retained in the release manifest.
Wrapper metadata does not replace a license audit of every VLC component or
the static-link relinking/source obligations for a future App Store release.

## GitHub Actions builds

Run **Build Apple dependencies** with a new immutable version:

```sh
gh workflow run build-dependencies.yml \
  --repo jacobjiangwei/CinavoDependencies --field version=2026.10.07.2
```

The workflow uses an arm64 `macos-26` runner and compiles FFmpeg from source for
all three SDKs. It restores only the checksum-verified `Pods/` snapshot pinned
in `prepared-pods.json`; it does not reuse old FFmpeg binaries or compile an
application. This avoids both a second private-repository credential and
CocoaPods/Ruby setup on the app's Xcode Cloud runners. GitHub's built-in
`GITHUB_TOKEN` downloads the seed and publishes the new private Release.

Each Release includes the runtime archive, SHA-256, per-file manifest and exact
FFmpeg source archive. Existing Releases are never overwritten. The consumer
must explicitly pin the new archive asset ID and SHA-256 in
`Cinavo/Configuration/Dependencies.lock.json`; it never downloads `latest`.

When changing VLC versions or the consumer Podfile, run the locked CocoaPods
installation locally and generate a new prepared snapshot:

```sh
python3 scripts/package_dependencies.py \
  --cinavo /path/to/tools/Cinavo --version NEW_VERSION
```

Publish that snapshot and update its tag, asset name and hashes in
`prepared-pods.json` before another cloud build. The cloud packager rejects
changed VLC specifications or Podfile hashes instead of silently mixing inputs.
