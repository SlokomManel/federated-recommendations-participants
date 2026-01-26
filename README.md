# Federated Recommendations

`federated-recommendations` is a **local** app that builds recommendations from your **Netflix viewing history** (your raw history stays on your machine).

It uses **SyftBox** to receive the latest **global model updates** and participate in federated learning without centralizing user data.

## Step 0 — Install `uv` (required)

If you already have `uv`, skip this step. If you see “uv not found”, do this first.

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS / Linux (Terminal)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then close/reopen your terminal so `uv` is on PATH.

## Step 1 — Prepare your Netflix viewing history

1. Netflix → **Account**
2. **Security & Privacy** → download/request your personal information
3. Unzip the export and find your viewing activity CSV (often named like `NetflixViewingHistory.csv`)

## Step 2 — Install SyftBox (and keep it running)

- **SyftBox home page**: `https://syftbox.net/`
- **SyftBox docs**: `https://syftbox-documentation.openmined.org/get-started`

SyftBox must be **running** while you use this app so you can receive the latest model updates.

### Windows

Install via terminal:

```bat
powershell -ExecutionPolicy ByPass -c "irm https://syftbox.net/install.ps1 | iex"
```


### macOS / Linux

```bash
curl -LsSf https://syftbox.openmined.org/install.sh | sh
```

Desktop app: install from `https://syftbox.net/` (supports auto-update + autostart).

### Keeping SyftBox running

- **Simplest**: keep SyftBox open in a **separate terminal/window** while running the app.
- **Most convenient**: use the desktop app installer and enable **autostart**.

## Step 3 — Clone the repository

You can clone this application anywhere on your machine.

### Windows

```powershell
git clone https://github.com/oussama-romdhane/syftbox-netflix-participant
cd .\federated-recommendations
```

### macOS / Linux

```bash
git clone https://github.com/oussama-romdhane/syftbox-netflix-participant
cd federated-recommendations
```

No `git`? You can also download the repo as a ZIP and extract it anywhere.

## Step 4 — Install & run the app

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

### macOS / Linux (Terminal)

```bash
chmod +x install.sh
./install.sh
```

Open the UI at:

- `http://localhost:8082`

## Running the app

If you have already installed the app, you don't need to run the installation script again. You can start it directly using:

```bash
uv run python app.py
```

## Troubleshooting

- **`uv` not found**: redo Step 0, then restart your terminal.
- **macOS/Linux “Permission denied”**: run `chmod +x install.sh`.