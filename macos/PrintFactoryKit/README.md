# PrintFactoryKit

Local-first macOS app for textile print production: artwork in → factory package out (print-ready files, tech pack, palette, checklist, ZIP). No cloud. Apple Silicon only.

## Run / build

```bash
cd macos/PrintFactoryKit
xcodegen generate   # brew install xcodegen
open PrintFactoryKit.xcodeproj
# or: xcodebuild -scheme PrintFactoryKit -configuration Release -derivedDataPath build ...
```

Requires macOS 26+, Xcode 26, Apple Silicon. Details: [`docs/user-guide.md`](docs/user-guide.md).

## Where things live

| Path | What |
|------|------|
| `PrintFactoryKit/` | App source (Swift) |
| `Tests/` | Tests |
| `docs/` | User guide + presentation |
| `assets/` | Screenshots / demo media |
| `archive/` | Old ZIP bundle (kept, not deleted) |
| `project.yml` | XcodeGen spec |

Part of [fulofilo-analytics](https://github.com/AUTOGIO/fulofilo-analytics). Agent rules: [`AGENTS.md`](AGENTS.md).
