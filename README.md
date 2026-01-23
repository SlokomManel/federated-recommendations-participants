# SyftBox Netflix BPR Participant

Participant application for the Netflix BPR federated learning recommendation system.

## Overview

This participant handles:
- Processing Netflix viewing history
- Local model fine-tuning (BPR)
- Generating personalized recommendations
- Serving the recommendation UI via FastAPI

## Setup

1. Install dependencies:
```bash
./install.sh
```

2. Configure `.env` file with your settings

3. Run the application:
```bash
uv run python app.py
```

## Structure

```
├── app.py               # FastAPI entry point + application
├── fetcher/             # Netflix data fetcher (Selenium)
├── loaders/             # Data loading utilities
├── participant_utils/   # SyftBox helpers
├── federated_learning/  # Participant-side FL (fine-tuning, recommendations)
├── recommender/         # Local recommendation generation
├── ui/                  # Web UI (HTML, CSS, JS)
└── data/                # Netflix titles and demo data
```

## How It Works

1. Fetches/loads Netflix viewing history
2. Processes viewing data into model format
3. Fine-tunes local user factors using BPR
4. Computes delta updates (with differential privacy)
5. Generates local recommendations using global model + local factors
6. Serves UI for browsing recommendations
