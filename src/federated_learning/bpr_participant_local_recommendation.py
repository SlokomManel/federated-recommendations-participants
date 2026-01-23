"""BPR local recommendation computation."""

import copy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def normalize_string(s):
    """Normalize a string by removing zero-width spaces and converting to lowercase."""
    return s.replace("\u200b", "").lower()


def mmr_rerank_predictions(unprocessed_predictions, lambda_param=0.3, top_n=50):
    """Maximal Marginal Relevance reranking for diversity."""
    model = SentenceTransformer("all-MiniLM-L6-v2")
    titles = [title for title, _, _ in unprocessed_predictions]
    embeddings = model.encode(titles, convert_to_tensor=False, show_progress_bar=False)

    ratings = np.array([pred_rating for _, _, pred_rating in unprocessed_predictions])
    ratings_normalized = (ratings - np.min(ratings)) / (np.max(ratings) - np.min(ratings))

    selected_indices = []
    candidate_indices = list(range(len(unprocessed_predictions)))

    while len(selected_indices) < min(top_n, len(unprocessed_predictions)):
        mmr_scores = []
        for idx in candidate_indices:
            relevance = ratings_normalized[idx]

            if not selected_indices:
                diversity_penalty = 0
            else:
                similarities = cosine_similarity(
                    embeddings[idx].reshape(1, -1),
                    embeddings[selected_indices]
                )[0]
                diversity_penalty = max(similarities)

            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            mmr_scores.append((idx, mmr_score))

        selected_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(selected_idx)
        candidate_indices.remove(selected_idx)

    return [unprocessed_predictions[i] for i in selected_indices]


def compute_recommendations(
    user_U,
    global_V,
    tv_vocab,
    user_aggregated_activity,
    recent_week=51,
    exclude_watched=True,
):
    """Compute recommendations based on user preferences and recent activity."""
    print("Selecting recommendations based on most recent shows watched...")

    recent_items = [
        title
        for (title, week, n_watched, rating) in user_aggregated_activity
        if int(week) == recent_week
    ]
    recent_item_ids = [tv_vocab[title] for title in recent_items if title in tv_vocab]
    print(f"For week (of all years) {recent_week}, watched n_shows=: {len(recent_items)}")

    U_recent = user_U

    all_items = list(tv_vocab.keys())
    watched_titles = set(
        normalize_string(t) for (t, _, _, _) in user_aggregated_activity
    )
    if exclude_watched:
        candidate_items = [
            title
            for title in all_items
            if normalize_string(title) not in watched_titles
        ]
    else:
        candidate_items = all_items
    
    predictions = []
    for title in candidate_items:
        item_id = tv_vocab[title]
        pred_rating = U_recent.dot(global_V[item_id])
        predictions.append((title, item_id, pred_rating))

    predictions.sort(key=lambda x: x[2], reverse=True)

    raw_predictions = copy.deepcopy(predictions)
    reranked_predictions = mmr_rerank_predictions(predictions, 0.3, 50)

    return raw_predictions[:50], reranked_predictions[:50]
