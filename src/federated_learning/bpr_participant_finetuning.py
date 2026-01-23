"""BPR participant fine-tuning for federated learning."""

import copy
import os
import random

import numpy as np

from src.services.data_loading import (
    load_global_item_factors,
    load_or_initialize_user_matrix,
    load_participant_ratings,
    load_tv_vocabulary,
)
from src.federated_learning.bpr_dp import (
    apply_differential_privacy,
    plot_ratings_norm,
)
from src.federated_learning.sequence_data import get_local_vocabulary_path


def save_training_results(user_id, private_path, restricted_path, V, delta_V, U_u):
    """
    Save the updated V matrix, delta_V, and user matrix to disk.

    Parameters:
        user_id (str): Identifier for the user.
        private_path: Path to private storage (for V and U).
        restricted_path: Path to restricted public folder (for delta_V - shared with aggregator).
        V (np.ndarray): Updated item factors matrix.
        delta_V (dict): Dictionary of delta updates for item factors.
        U_u (np.ndarray): Updated user matrix.
    """
    user_private_path = os.path.join(private_path, "svd_training")
    user_restricted_path = os.path.join(restricted_path, "svd_training")
    os.makedirs(user_private_path, exist_ok=True)
    os.makedirs(user_restricted_path, exist_ok=True)

    # Save updated V (private)
    participant_v_save_path = os.path.join(user_private_path, "updated_V.npy")
    np.save(participant_v_save_path, V)

    # Save delta_V (shared with aggregator)
    participant_deltav_save_path = os.path.join(user_restricted_path, "delta_V.npy")
    np.save(participant_deltav_save_path, delta_V)

    # Save updated user matrix (private)
    user_matrix_path = os.path.join(user_private_path, "U.npy")
    np.save(user_matrix_path, U_u)

    print(f"Saved private training results for user: {user_id} at {user_private_path}.")
    print(f"Saved delta updates for user: {user_id} at {user_restricted_path}.")


def prepare_training_data(user_id, tv_vocab, final_ratings):
    """Prepare training data for the participant."""
    item_ids = {title: tv_vocab[title] for title in final_ratings if title in tv_vocab}
    return [
        (user_id, item_ids[t], final_ratings[t]) for t in final_ratings if t in item_ids
    ]


def perform_local_training(
    train_data, initial_V, initial_U_u, alpha=0.01, lambda_reg=0.1, iterations=10
):
    """
    Perform local training for the participant using BPR (FedBPR-style).
    
    Args:
        train_data: list of (user_id, item_id, rating)
        initial_V: item factors matrix
        initial_U_u: user factors vector
        alpha: learning rate
        lambda_reg: regularization parameter
        iterations: number of training iterations
    
    Returns:
        tuple: (initial_V, updated_V, updated_U_u)
    """
    V = copy.deepcopy(initial_V)
    U_u = copy.deepcopy(initial_U_u)

    # Hyperparameters from FedBPR paper
    user_reg = alpha / 20
    pos_item_reg = alpha / 20
    neg_item_reg = alpha / 200

    # Build item sets
    positive_items = list({item for _, item, _ in train_data})
    all_items = list(range(len(V)))
    negative_items = list(set(all_items) - set(positive_items))

    # No negative items means user watched everything - can't train
    if not negative_items:
        return initial_V, V, U_u

    # BPR learning
    for _ in range(iterations):
        for pos_item in positive_items:
            if not negative_items:
                continue
            neg_item = random.choice(negative_items)

            # BPR gradient update
            x_u_pos = U_u.dot(V[pos_item])
            x_u_neg = U_u.dot(V[neg_item])
            x_uij = x_u_pos - x_u_neg
            sigmoid_grad = 1 / (1 + np.exp(x_uij))  # dL/dx from BPR

            # Compute gradients
            user_grad = sigmoid_grad * (V[pos_item] - V[neg_item]) - user_reg * U_u
            pos_item_grad = sigmoid_grad * U_u - pos_item_reg * V[pos_item]
            neg_item_grad = -sigmoid_grad * U_u - neg_item_reg * V[neg_item]

            # Apply updates
            U_u += alpha * user_grad
            V[pos_item] += alpha * pos_item_grad
            V[neg_item] += alpha * neg_item_grad

    return initial_V, V, U_u


def participant_fine_tuning(
    user_id,
    private_path,
    global_path,
    restricted_path,
    epsilon=None,
    clipping_threshold=None,
    noise_type="gaussian",
    plot=False,
    dp_all=False,
):
    """
    Orchestrator function for participant fine-tuning.
    
    Args:
        user_id: Identifier for the participant/profile
        private_path: Path to private data storage
        global_path: Path to shared folder (contains global_V.npy and vocabulary)
        restricted_path: Path to restricted public folder (aggregator can read delta_V)
        epsilon: Privacy budget for differential privacy (None = no DP)
        clipping_threshold: Threshold for gradient clipping
        noise_type: Type of DP noise ('gaussian' or 'laplace')
        plot: Whether to plot delta distributions
        dp_all: Apply DP to all items, not just trained ones
    
    Returns:
        dict: The differentially private deltas (delta_V)
    """
    # Step 1: Load vocabulary
    try:
        vocabulary_path = os.path.join(global_path, "tv-series_vocabulary.json")
        tv_vocab = load_tv_vocabulary(vocabulary_path)
        print(f"Loaded TV series vocabulary from {vocabulary_path}.")
    except FileNotFoundError:
        vocabulary_path = get_local_vocabulary_path()
        tv_vocab = load_tv_vocabulary(str(vocabulary_path))
        print(f"Loaded TV series vocabulary from local file: {vocabulary_path}.")

    # Step 2: Load global item factors
    V = load_global_item_factors(global_path)

    # Step 3: Load participant's ratings
    final_ratings = load_participant_ratings(private_path)

    # Step 4: Load or initialize user matrix
    U_u = load_or_initialize_user_matrix(
        user_id, V.shape[1], save_path=os.path.join(private_path, "svd_training")
    )

    # Step 5: Prepare training data
    train_data = prepare_training_data(user_id, tv_vocab, final_ratings)
    if not train_data:
        raise ValueError(
            "No training items after mapping participant ratings to vocabulary. "
            "This indicates `ratings.npy` keys don't match the vocabulary titles "
            "(or ratings is empty)."
        )

    # Step 6: Perform local training
    initial_V, updated_V, updated_U_u = perform_local_training(train_data, V, U_u)

    # Step 7: Compute deltas
    if dp_all:
        delta_V = {
            item_id: updated_V[item_id] - initial_V[item_id]
            for item_id, _ in enumerate(initial_V)
        }
    else:
        delta_V = {
            item_id: updated_V[item_id] - initial_V[item_id]
            for (_, item_id, _) in train_data
        }

    delta_norms_before = [np.linalg.norm(v) for v in delta_V.values()]

    # Step 8: Apply differential privacy
    dp_deltas = apply_differential_privacy(
        delta_V, epsilon, 0.36, noise_type=noise_type
    )

    delta_norms_after = [np.linalg.norm(v) for v in dp_deltas.values()]

    # Step 9: Save results
    save_training_results(
        user_id, private_path, restricted_path, updated_V, dp_deltas, updated_U_u
    )

    # Step 10: Optional plotting
    if plot:
        sorted_item_ids = sorted(delta_V.keys())
        plot_ratings_norm(
            user_id, sorted_item_ids, delta_norms_before, delta_norms_after
        )

    print(f"Participant {user_id} finished training and updated item factors.")
    return dp_deltas
