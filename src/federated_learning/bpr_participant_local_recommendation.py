"""BPR local recommendation computation."""

import copy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging

from src.config import NORMALIZE_ITEM_FACTORS, ITEM_FACTOR_NORM_METHOD, ITEM_FACTOR_NORM_TARGET


def normalize_string(s):
    """Normalize a string by removing zero-width spaces and converting to lowercase."""
    return s.replace("\u200b", "").lower()


def mmr_rerank_predictions(unprocessed_predictions, lambda_param=0.3, top_n=50, normalize_scores=True):
    """Maximal Marginal Relevance reranking for diversity.

    normalize_scores: whether to min-max normalize the ratings before computing MMR.
    If False, the ratings are used as provided (useful if recommendations are already normalized).
    """
    model = SentenceTransformer("all-MiniLM-L6-v2")
    titles = [title for title, _, _ in unprocessed_predictions]
    embeddings = model.encode(titles, convert_to_tensor=False, show_progress_bar=False)

    ratings = np.array([pred_rating for _, _, pred_rating in unprocessed_predictions])
    if normalize_scores:
        min_r = np.min(ratings)
        max_r = np.max(ratings)
        if max_r - min_r == 0:
            ratings_normalized = np.zeros_like(ratings)
        else:
            ratings_normalized = (ratings - min_r) / (max_r - min_r)
    else:
        ratings_normalized = ratings.copy()

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


import logging


def compute_recommendations(
    user_U,
    global_V,
    tv_vocab,
    user_aggregated_activity,
    recent_week=51,
    exclude_watched=True,
    score_normalization=None,  # None | 'sigmoid' | 'minmax'
    normalize_item_factors=None,  # None -> use config.NORMALIZE_ITEM_FACTORS | True/False override
    item_factor_norm_method=None,  # 'l2' | 'scale_mean' (overrides config)
    item_factor_norm_target=None,  # float (overrides config.ITEM_FACTOR_NORM_TARGET)
):
    """Compute recommendations based on user preferences and recent activity.

    score_normalization: optional strategy to normalize predicted scores for interpretability.
        - None: leave raw scores
        - 'sigmoid': apply sigmoid to scores -> (0,1)
        - 'minmax': min-max normalize scores to [0,1] per-user

    normalize_item_factors: optional flag to normalize or scale item factors before scoring.
        - None: use config `NORMALIZE_ITEM_FACTORS`
        - True: enable normalization
        - False: disable normalization

    item_factor_norm_method: if normalization enabled, one of 'l2' (unit L2 rows) or 'scale_mean' (scale to target mean norm)
    item_factor_norm_target: used by 'scale_mean' to set the target mean norm (float)
    """
    logging.debug("Selecting recommendations based on most recent shows watched...")

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

    # Optionally normalize/scale global item factors before scoring
    if normalize_item_factors is None:
        normalize_item_factors = NORMALIZE_ITEM_FACTORS
    if normalize_item_factors:
        method = item_factor_norm_method or ITEM_FACTOR_NORM_METHOD
        target = item_factor_norm_target or ITEM_FACTOR_NORM_TARGET
        try:
            norms = np.linalg.norm(global_V, axis=1)
            mean_norm = float(np.mean(norms))
            max_norm = float(np.max(norms))
            logging.info(f"Item factor norms before normalization: mean={mean_norm:.4f}, max={max_norm:.4f}")
            V_for_scoring = global_V.copy()
            if method == "l2":
                nonzero = norms > 0
                V_for_scoring[nonzero] = V_for_scoring[nonzero] / norms[nonzero][:, None]
            elif method == "scale_mean":
                if mean_norm > 0:
                    scale = float(target) / mean_norm
                    V_for_scoring = V_for_scoring * scale
            else:
                logging.warning(f"Unknown ITEM_FACTOR_NORM_METHOD: {method}. Skipping normalization.")
                V_for_scoring = global_V
            # Log post-normalization mean norm
            post_norms = np.linalg.norm(V_for_scoring, axis=1)
            logging.info(f"Item factor norms after normalization: mean={float(np.mean(post_norms)):.4f}, max={float(np.max(post_norms)):.4f}")
        except Exception as e:
            logging.error(f"Failed to normalize item factors: {e}")
            V_for_scoring = global_V
    else:
        V_for_scoring = global_V

    predictions = []
    for title in candidate_items:
        item_id = tv_vocab[title]
        pred_rating = U_recent.dot(V_for_scoring[item_id])
        predictions.append((title, item_id, pred_rating))

    # Diagnostic: log raw score stats before any normalization
    try:
        import numpy as _np
        raw_scores = _np.array([s for _, _, s in predictions], dtype=float)
        if raw_scores.size:
            logging.debug(f"Raw score stats: min={raw_scores.min():.6f}, max={raw_scores.max():.6f}, mean={raw_scores.mean():.6f}")
            # Warn if raw scores exceed 1 (unexpected for this dataset)
            if raw_scores.max() > 1.0:
                # Show top samples for inspection
                sorted_idx = _np.argsort(raw_scores)[::-1]
                sample_idx = sorted_idx[:10]
                sample_pairs = [(predictions[i][0], float(raw_scores[i])) for i in sample_idx]
                logging.warning(
                    f"Unexpected raw score magnitudes (max > 1). Top samples: {sample_pairs}. U_norm={_np.linalg.norm(user_U):.4f}, V_mean_norm={_np.mean([_np.linalg.norm(global_V[tv_vocab[k]]) for k in list(tv_vocab.keys())]):.4f}"
                )
        else:
            logging.debug("Raw scores empty")
    except Exception:
        logging.debug("Could not compute raw score stats")

    # Optional per-user score normalization for interpretability (None | 'sigmoid' | 'minmax')
    if score_normalization == "sigmoid":
        import numpy as _np
        predictions = [
            (t, i, float(1 / (1 + _np.exp(-s)))) for (t, i, s) in predictions
        ]
    elif score_normalization == "minmax":
        import numpy as _np
        scores = _np.array([s for _, _, s in predictions], dtype=float)
        if scores.size == 0:
            normalized_scores = scores
        else:
            min_s = float(scores.min())
            max_s = float(scores.max())
            if max_s - min_s == 0:
                normalized_scores = _np.zeros_like(scores)
            else:
                normalized_scores = (scores - min_s) / (max_s - min_s)
        predictions = [
            (title, item_id, float(normalized_scores[idx]))
            for idx, (title, item_id, _) in enumerate(predictions)
        ]

    # Diagnostic: log post-normalization stats and warn if values outside [0,1]
    try:
        import numpy as _np
        post_scores = _np.array([s for _, _, s in predictions], dtype=float)
        if post_scores.size:
            logging.debug(f"Post-norm score stats ({score_normalization}): min={post_scores.min():.6f}, max={post_scores.max():.6f}, mean={post_scores.mean():.6f}")
            if score_normalization in ("sigmoid", "minmax"):
                if post_scores.min() < -1e-6 or post_scores.max() > 1 + 1e-6:
                    logging.warning(f"Normalized scores outside [0,1]: min={post_scores.min():.6f}, max={post_scores.max():.6f}")
        else:
            logging.debug("Post-norm scores empty")
    except Exception:
        logging.debug("Could not compute post-normalization stats")

    predictions.sort(key=lambda x: x[2], reverse=True)

    raw_predictions = copy.deepcopy(predictions)
    # If we already normalized scores above, tell MMR not to re-normalize
    reranked_predictions = mmr_rerank_predictions(
        predictions, 0.3, 50, normalize_scores=(score_normalization is None)
    )

    return raw_predictions[:50], reranked_predictions[:50]
