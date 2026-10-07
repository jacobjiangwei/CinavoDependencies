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
