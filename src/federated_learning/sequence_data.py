"""Sequence data processing for Netflix viewing history."""

import json
import logging
import os
import re
from datetime import datetime

import numpy as np
import pandas as pd
from rapidfuzz import process

class SequenceData:
    """Process Netflix viewing data into sequential format."""

    def __init__(self, dataset: np.ndarray):
        self.dataset = dataset
        self.aggregated_data = self.process_dataset()

    def parse_date_str(self, date_str):
        formats = ["%d/%m/%Y", "%m/%d/%y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return pd.NaT

    def extract_features(self, df):
        df["show"] = df["Title"].apply(lambda x: x.split(":")[0] if ":" in x else x)
        df["season"] = df["Title"].apply(
            lambda x: int(re.search(r"Season (\d+)", x).group(1))
            if re.search(r"Season (\d+)", x)
            else 0
        )
        df["Date"] = df["Date"].apply(self.parse_date_str)
        df["day_of_week"] = df["Date"].dt.dayofweek
        return df

    def process_dataset(self):
        """Organize data sequentially from oldest to newest."""
        df = pd.DataFrame(self.dataset, columns=["Title", "Date"])
        df = self.extract_features(df).copy()
        df_aggregated = (
            df.groupby("show")
            .agg(Total_Views=("Date", "size"), First_Seen=("Date", "min"))
            .reset_index()
        )
        df_aggregated = df_aggregated.sort_values(
            by="First_Seen", ascending=True
        ).reset_index(drop=True)

        df_filtered = df_aggregated[df_aggregated["Total_Views"] > 1].reset_index(drop=True)
        return df_filtered


def match_title(title, vocabulary: dict, threshold=80):
    """Match title to vocabulary using exact or fuzzy matching."""
    if title in vocabulary:
        return vocabulary[title]

    vocab_keys = list(vocabulary.keys())
    match_result = process.extractOne(title, vocab_keys)

    if match_result is not None:
        best_match, score = match_result[:2]
        if score >= threshold:
            return vocabulary[best_match]

    return -1


def create_view_counts_vector(restricted_shared_folder, aggregated_data: pd.DataFrame) -> np.ndarray:
    """Create sparse vector of view counts."""
    shared_file = os.path.join(restricted_shared_folder, "vocabulary.json")
    with open(shared_file, "r", encoding="utf-8") as file:
        vocabulary = json.load(file)

    aggregated_data["ID"] = aggregated_data["show"].apply(lambda x: match_title(x, vocabulary))

    vector_size = len(vocabulary)
    sparse_vector = np.zeros(vector_size, dtype=int)

    for _, row in aggregated_data.iterrows():
        if row["ID"] != -1:
            sparse_vector[row["ID"]] += row["Total_Views"]

    unmatched_titles = aggregated_data[aggregated_data["ID"] == -1]["show"].tolist()
    logging.info(f"(create_view_counts_vector) Unmatched Titles: {unmatched_titles}")

    return sparse_vector
