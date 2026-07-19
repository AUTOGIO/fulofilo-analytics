# AGENTS.md — PrintFactoryKit

Native macOS app (Apple Silicon) for factory-ready print packages. Part of fulofilo-analytics under `macos/PrintFactoryKit`.

## Folder layout

| Path | Purpose |
|------|---------|
| `PrintFactoryKit/` | Application source (SwiftUI) — keep this name; Xcode depends on it |
| `Tests/` | Unit tests only |
| `docs/` | Guides and presentation (`user-guide.md`, `presentation.html`) |
| `docs/prompts/` | AI prompt files (if added) |
| `assets/` | Screenshots, icons, demo media |
| `archive/` | Obsolete bundles (e.g. old `.zip`) — do not delete without asking |
| `scripts/` | Runnable helpers (if added) |
| `config/` | Non-secret settings (if added) |
| `data/` | Sample inputs / exports (if added) |

**Root of this kit** stays lean: `README.md`, `AGENTS.md`, `.gitignore`, `project.yml`, and the Xcode project.

Prefer **move** over copy. Prefer **edit** over create. Do not invent new top-level folders here without asking. No secrets in git.

## Build

```bash
xcodegen generate
xcodebuild -scheme PrintFactoryKit -configuration Release -derivedDataPath build \
  CODE_SIGN_IDENTITY="-" CODE_SIGNING_REQUIRED=NO CODE_SIGNING_ALLOWED=NO build
```

`build/` and `dist/` are local only (gitignored).
