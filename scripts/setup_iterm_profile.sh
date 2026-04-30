#!/bin/zsh
# FulôFiló — Install iTerm2 Dynamic Profile
# ─────────────────────────────────────────────────────────────────────────────
# Creates a "FulôFiló" profile in iTerm2 using the HUD dark theme.
# Run once: bash scripts/setup_iterm_profile.sh
#
# Color palette (matches the dashboard HUD):
#   Background : #080C18  (deep navy)
#   Foreground : #E2E8F0  (light slate)
#   Cursor     : #00FF88  (neon green)
#   Accent     : #00D4FF  (electric cyan)
#   Gold       : #FFD700
#   Red        : #FF4455
#   Purple     : #A78BFA
# ─────────────────────────────────────────────────────────────────────────────

PROFILE_DIR="$HOME/Library/Application Support/iTerm2/DynamicProfiles"
PROFILE_FILE="$PROFILE_DIR/FuloFilo.json"

mkdir -p "$PROFILE_DIR"

cat > "$PROFILE_FILE" <<'JSON'
{
  "Profiles": [
    {
      "Name": "FulôFiló",
      "Guid": "fulofilo-hud-terminal-v1",
      "Custom Command": "No",
      "Custom Directory": "Yes",
      "Working Directory": "/Users/giovannini_nuovo/Documents/GitHub/FuloFilo",
      "Terminal Type": "xterm-256color",
      "Rows": 32,
      "Columns": 110,

      "Normal Font": "MesloLGMNerdFontComplete-Regular 13",
      "Non Ascii Font": "MesloLGMNerdFontComplete-Regular 13",
      "Use Non-ASCII Font": false,
      "ASCII Anti Aliased": true,

      "Background Color": {
        "Red Component":   0.0314,
        "Green Component": 0.0471,
        "Blue Component":  0.0941,
        "Alpha Component": 1.0
      },
      "Foreground Color": {
        "Red Component":   0.8863,
        "Green Component": 0.9098,
        "Blue Component":  0.9412,
        "Alpha Component": 1.0
      },
      "Cursor Color": {
        "Red Component":   0.0,
        "Green Component": 1.0,
        "Blue Component":  0.5333,
        "Alpha Component": 1.0
      },
      "Cursor Text Color": {
        "Red Component":   0.0314,
        "Green Component": 0.0471,
        "Blue Component":  0.0941,
        "Alpha Component": 1.0
      },
      "Selection Color": {
        "Red Component":   0.0,
        "Green Component": 0.2039,
        "Blue Component":  0.3137,
        "Alpha Component": 1.0
      },
      "Selected Text Color": {
        "Red Component":   0.8863,
        "Green Component": 0.9098,
        "Blue Component":  0.9412,
        "Alpha Component": 1.0
      },
      "Bold Color": {
        "Red Component":   0.0,
        "Green Component": 0.8314,
        "Blue Component":  1.0,
        "Alpha Component": 1.0
      },
      "Link Color": {
        "Red Component":   0.0,
        "Green Component": 0.8314,
        "Blue Component":  1.0,
        "Alpha Component": 1.0
      },

      "Ansi 0 Color":  {"Red Component": 0.0314, "Green Component": 0.0471,  "Blue Component": 0.0941,  "Alpha Component": 1.0},
      "Ansi 1 Color":  {"Red Component": 1.0,    "Green Component": 0.2667,  "Blue Component": 0.3333,  "Alpha Component": 1.0},
      "Ansi 2 Color":  {"Red Component": 0.0,    "Green Component": 1.0,     "Blue Component": 0.5333,  "Alpha Component": 1.0},
      "Ansi 3 Color":  {"Red Component": 1.0,    "Green Component": 0.8431,  "Blue Component": 0.0,     "Alpha Component": 1.0},
      "Ansi 4 Color":  {"Red Component": 0.0,    "Green Component": 0.8314,  "Blue Component": 1.0,     "Alpha Component": 1.0},
      "Ansi 5 Color":  {"Red Component": 0.6549, "Green Component": 0.5451,  "Blue Component": 0.9804,  "Alpha Component": 1.0},
      "Ansi 6 Color":  {"Red Component": 0.0,    "Green Component": 0.8314,  "Blue Component": 1.0,     "Alpha Component": 1.0},
      "Ansi 7 Color":  {"Red Component": 0.8863, "Green Component": 0.9098,  "Blue Component": 0.9412,  "Alpha Component": 1.0},
      "Ansi 8 Color":  {"Red Component": 0.2784, "Green Component": 0.3294,  "Blue Component": 0.4157,  "Alpha Component": 1.0},
      "Ansi 9 Color":  {"Red Component": 1.0,    "Green Component": 0.2667,  "Blue Component": 0.3333,  "Alpha Component": 1.0},
      "Ansi 10 Color": {"Red Component": 0.0,    "Green Component": 1.0,     "Blue Component": 0.5333,  "Alpha Component": 1.0},
      "Ansi 11 Color": {"Red Component": 1.0,    "Green Component": 0.8431,  "Blue Component": 0.0,     "Alpha Component": 1.0},
      "Ansi 12 Color": {"Red Component": 0.0,    "Green Component": 0.8314,  "Blue Component": 1.0,     "Alpha Component": 1.0},
      "Ansi 13 Color": {"Red Component": 0.6549, "Green Component": 0.5451,  "Blue Component": 0.9804,  "Alpha Component": 1.0},
      "Ansi 14 Color": {"Red Component": 0.0,    "Green Component": 0.8314,  "Blue Component": 1.0,     "Alpha Component": 1.0},
      "Ansi 15 Color": {"Red Component": 0.8863, "Green Component": 0.9098,  "Blue Component": 0.9412,  "Alpha Component": 1.0},

      "Cursor Type": 1,
      "Blinking Cursor": true,
      "Transparency": 0.04,
      "Blur": true,
      "Blur Radius": 6.0,

      "Badge Text": "FulôFiló",
      "Badge Color": {
        "Red Component":   0.0,
        "Green Component": 0.8314,
        "Blue Component":  1.0,
        "Alpha Component": 0.45
      },

      "Scrollback Lines": 5000,
      "Unlimited Scrollback": false,
      "Mouse Reporting": true,
      "Allow Title Reporting": false,
      "Allow Title Setting": true
    }
  ]
}
JSON

echo ""
echo "  ✅  FulôFiló profile installed at:"
echo "      $PROFILE_FILE"
echo ""
echo "  iTerm2 picks it up automatically — no restart needed."
echo "  The profile will appear as 'FulôFiló' in iTerm2 → Profiles."
echo ""
echo "  To use immediately: Profiles → FulôFiló → Open"
echo ""
