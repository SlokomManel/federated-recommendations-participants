# Installation Guide — macOS

Welcome! Follow these steps to set up the Federated Recommendations app on macOS.

---

## ⏱️ Important: Installation Timeline

**Installation may take a few minutes** — SyftBox needs a few minutes to synchronize with the aggregator on first run. This is normal and expected. Just follow along at your own pace.

**If you see an error** — close the app, wait **up to 10 minutes**, then try again. Most errors are temporary and will resolve on their own.

---

## Step 1 — Install `uv` (if you don't have it)

`uv` is a fast Python package manager. Check if you already have it by opening Terminal and typing:

```bash
uv --version
```

**If you see a version number**, skip to Step 2. **If you see "command not found"**, install it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen Terminal so `uv` is available.

---

## Step 2 — Download your Netflix viewing history

Download your Netflix viewing activity as a CSV file from your Netflix account. [See how to download your Netflix History](https://help.netflix.com/en/node/101917) 

**Important notes:**
- You are free to delete movies that you do not want to upload to the app!
- Your movies will remain local/private and not shared with the aggregator

---

## Step 3 — Install SyftBox

SyftBox is how you sync with the research aggregator. You have two options:

### Option A: Desktop App (Recommended for easiest setup)

1. Visit https://syftbox.net/
2. Download and install the desktop app
3. Open the app after installation
4. SyftBox will start automatically and sync with the aggregator (may take a few minutes)

**Benefit**: SyftBox runs in the background and can auto-start when you restart your machine.

### Option B: Terminal Installation

If you prefer terminal, run:

```bash
curl -LsSf https://syftbox.openmined.org/install.sh | sh
```

Then keep SyftBox running in a separate Terminal window while you use the recommendation app. Start it with:

```bash
syftbox
```

---

## Step 4 — Clone this app

Choose a location on your machine where you want the app to live, then open Terminal and run:

```bash
git clone https://github.com/SlokomManel/federated-recommendations-participants.git
cd federated-recommendations-participants
```

Don't have `git`? You can also [download the repo as a ZIP](https://github.com/SlokomManel/federated-recommendations-participants/archive/refs/heads/main.zip), extract it, and open Terminal inside that folder.

---

## Step 5 — Install the app

From inside the `federated-recommendations-participants` folder, run:

```bash
chmod +x install.sh
./install.sh
```

This will install all dependencies. Let it finish (it may take a minute).

---

## Step 6 — Run the app

Now you're ready! To start the recommendation app, run:

```bash
uv run python app.py
```

You should see a message like:
```
Uvicorn running on http://0.0.0.0:8082
```

Open your browser and go to: **http://localhost:8082**

---

## Uploading your Netflix history

When the app loads, you'll see a prompt to upload your Netflix viewing history. Use the CSV file you downloaded in Step 2.

The app will process it locally on your machine (we never send it anywhere).

---

## How to run next time

Once installed, you don't need to run `install.sh` again. Just use:

```bash
uv run python app.py
```

---

## Keeping SyftBox running

While using the recommendation app:
- If you installed via **desktop app**: it runs in the background automatically
- If you installed via **terminal**: keep the terminal window with `syftbox` running in the background

---

## Troubleshooting

**`uv` command not found**
- Redo Step 1 and make sure to close/reopen Terminal after installation

**"Permission denied" when running install.sh**
- Run: `chmod +x install.sh` then try again

**App won't start or shows an error**
- Make sure SyftBox is running (check Step 3)
- Close the app, wait **up to 10 minutes**, then try again
- Check that your Netflix history CSV is in the correct format

**SyftBox won't sync**
- Wait a few minutes (the initial sync can be slow)
- Try closing SyftBox and opening it again
- Make sure you have an internet connection

---

**Questions?** Refer back to the main [README](README.md) or check the [SyftBox documentation](https://syftbox-documentation.openmined.org/).
