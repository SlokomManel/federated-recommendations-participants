"""Quick demo showing effect of item-factor normalization on scores."""
import numpy as np
from src.federated_learning.bpr_participant_local_recommendation import compute_recommendations

# Create toy V with large norms
V = np.array([[5.0, -3.0], [0.2, 0.1], [2.0, 1.0]])
U = np.array([0.1, 0.05])

vocab = {"A":0, "B":1, "C":2}
activity = np.array([['A',51,1,3.0]], dtype=object)

print("Raw scores (no normalization):")
raw, _ = compute_recommendations(U, V, vocab, activity, recent_week=51, exclude_watched=False, score_normalization=None, normalize_item_factors=False)
print(raw)

print("L2-normalized item vectors:")
raw_l2, _ = compute_recommendations(U, V, vocab, activity, recent_week=51, exclude_watched=False, score_normalization=None, normalize_item_factors=True, item_factor_norm_method='l2')
print(raw_l2)

print("Scale-mean normalization to target mean=1.0:")
raw_scale, _ = compute_recommendations(U, V, vocab, activity, recent_week=51, exclude_watched=False, score_normalization=None, normalize_item_factors=True, item_factor_norm_method='scale_mean', item_factor_norm_target=1.0)
print(raw_scale)
