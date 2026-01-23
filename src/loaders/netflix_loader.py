"""Netflix data loading utilities."""

import os
from datetime import datetime
from pathlib import Path

import yaml

from src.fetcher.netflix_fetcher import NetflixFetcher


def participants_yaml_datasets(
    datasite_path: Path, dataset_name="Netflix Data", dataset_format="CSV"
):
    """Check for dataset in datasites/<user>/public/datasets.yaml"""
    datasets_yaml = Path(datasite_path / "public" / "datasets.yaml")
    if datasets_yaml.is_file():
        with open(datasets_yaml, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

            for dataset in data.get("datasets", []):
                if (
                    dataset.get("name") == dataset_name
                    and dataset.get("format") == dataset_format
                    and "path" in dataset
                ):
                    return dataset.get("path")
            return None


def download_daily_data(output_dir: str, file_name: str, profile: str = None) -> None:
    """Download Netflix data into today's subfolder."""
    downloader = NetflixFetcher(output_dir, profile)
    downloader.run()

    file_path = os.path.join(output_dir, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Netflix viewing history file was not created: {file_path}")


def get_latest_file(subfolder_path, csv_name):
    """Get the latest file in the subfolder by datetime in filename."""
    netflix_csv_prefix = os.path.splitext(csv_name)[0] + "_"

    files = [
        f
        for f in os.listdir(subfolder_path)
        if os.path.isfile(os.path.join(subfolder_path, f))
        and f.startswith(netflix_csv_prefix)
    ]

    if not files:
        raise FileNotFoundError(f"No files found in {subfolder_path}")

    def extract_datetime(filename):
        try:
            date_str = filename.replace(netflix_csv_prefix, "").replace(".csv", "")
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    files_with_dates = [(f, extract_datetime(f)) for f in files]
    valid_files = [(f, dt) for f, dt in files_with_dates if dt is not None]

    if not valid_files:
        raise FileNotFoundError(f"No valid files with dates found in {subfolder_path}")

    latest_file = max(valid_files, key=lambda x: x[1])[0]
    return os.path.join(subfolder_path, latest_file)
