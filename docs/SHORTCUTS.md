# FulôFiló — macOS Shortcuts & Automation

## Automated ETL via Folder Watch

### Overview
Drop a new Eleve Vendas JSON export into a watched inbox folder.
macOS Shortcuts detects the new file and triggers the full ETL pipeline automatically.

### Setup (macOS Sequoia / Tahoe)

#### 1. Create the Inbox Folder
```bash
mkdir -p ~/Documents/FuloFilo_Inbox/processed
```

#### 2. Create the macOS Shortcut

Open **Shortcuts.app** → New Shortcut → name it `FulôFiló Auto-Refresh`

Add these actions in order:

| Step | Action | Settings |
|------|--------|---------|
| 1 | **Get Contents of Folder** | `~/Documents/FuloFilo_Inbox` |
| 2 | **Filter Files** | Name ends with `.json` |
| 3 | **If** | File count > 0 |
| 4 | **Run Shell Script** | See script below |
| 5 | **Show Notification** | "FulôFiló dados atualizados ✅" |

Shell Script content for Step 4:
```bash
/bin/bash /Users/eduardogiovannini/dev/products/FuloFilo/scripts/refresh_data.sh
```

#### 3. Set Up Folder Automation (Automator)

As an alternative to Shortcuts, use **Automator**:
1. Open Automator → New → Folder Action
2. Watch folder: `~/Documents/FuloFilo_Inbox`
3. Add action: **Run Shell Script**
4. Script: `/bin/bash /Users/eduardogiovannini/dev/products/FuloFilo/scripts/refresh_data.sh`
5. Save as `FuloFilo_Auto_Refresh`
6. Right-click the Inbox folder → Services → Folder Actions Setup → enable

#### 4. Test the Pipeline

```bash
# Manual test
cp /path/to/new_eleve_export.json ~/Documents/FuloFilo_Inbox/
# Wait ~5 seconds — Automator should trigger
# Check logs:
tail -f /Users/eduardogiovannini/dev/products/FuloFilo/logs/refresh.log
```

## Manual Launch

```bash
# Start the analytics dashboard
./scripts/launch_app.sh

# Run refresh manually
./scripts/refresh_data.sh

# Generate Excel report
.venv/bin/python3 excel/build_report.py
```

## Keyboard Shortcuts in the App

| Action | Shortcut |
|--------|---------|
| Refresh page | `R` |
| Toggle sidebar | `S` |
| Dark/light mode | In settings (☰) |
