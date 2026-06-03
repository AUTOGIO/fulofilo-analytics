#!/usr/bin/env bash
# Build native FF Terminal (SwiftPM) for Apple Silicon macOS.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG="$ROOT/macos/FuloFiloTerminal"
BIN="$PKG/.build/release/FuloFiloTerminal"

if ! command -v swift >/dev/null 2>&1; then
  echo "Xcode Command Line Tools required. Run: xcode-select --install" >&2
  exit 1
fi

cd "$PKG"
echo "Building FuloFiloTerminal (release)..."
swift build -c release
if [ ! -x "$BIN" ]; then
  echo "Build failed: $BIN not found" >&2
  exit 1
fi
echo "Built: $BIN"
