# SIMORGH AppImage

SIMORGH provides a self-contained Linux AppImage for first-time users. The AppImage contains the application source, the core Python runtime, core Python dependencies, the web UI, and the canonical read-only knowledge database. User memory, imports, logs, configuration, and downloaded models remain outside the AppImage in the user's XDG data/config directories.

## Run

Download the architecture-matched `SIMORGH-x86_64.AppImage`, make it executable, and launch it. No Python, pip, Git, or SIMORGH account is required on the host.

```bash
chmod +x SIMORGH-x86_64.AppImage
./SIMORGH-x86_64.AppImage
```

On first launch, a graphical directory chooser is used when `zenity` or `kdialog` is available. Otherwise `~/.local/share/simorgh` is used. The application listens only on `127.0.0.1` by default.

## User data boundary

The AppImage is treated as read-only. Persistent user state is stored outside the image:

```text
~/.local/share/simorgh/
~/.config/simorgh/
```

The bundled knowledge database is used as a read-only source. A user's writable application database is initialized under the external runtime directory.

## No-model operation

A language model is not required to start SIMORGH. The application keeps its deterministic local knowledge path available when no local model backend is configured.

## Local models

Model installation remains an explicit user action. The model manager checks hardware compatibility and a pinned SHA-256 digest before registering a downloaded model. Imported local files are hashed and recorded without inventing trusted provenance.

A local llama.cpp backend is downloaded only when the user selects a model that needs it. The backend release archive is verified by SHA-256 before extraction and is run on loopback only.

## Building

The repository build script uses an immutable Python-build-standalone release for CPython 3.13.15 and a SHA-pinned AppImage tool. The GitHub Actions workflow performs the same build on Ubuntu 22.04, materializes the Git LFS database, checks SQLite integrity, and smoke-tests the resulting AppImage.

```bash
packaging/build-appimage.sh
```

The build output is:

```text
dist/SIMORGH-x86_64.AppImage
```

A versioned Git tag (`v*`) causes the workflow to attach the generated AppImage to a GitHub release. Manual workflow dispatch is also supported.

## Portability boundary

This first release targets x86_64 Linux. AppImage portability still depends on the host kernel and userspace graphics/runtime environment. The build is intentionally based on Ubuntu 22.04 rather than the developer's local machine, and the application itself avoids mandatory system Python dependencies.
