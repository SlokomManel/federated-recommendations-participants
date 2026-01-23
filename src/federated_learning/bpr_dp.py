"""Differential privacy utilities for BPR."""

import copy
import numpy as np
import matplotlib.pyplot as plt


def calculate_optimal_threshold(delta_V, method="median"):
    """Calculate the optimal threshold for clipping deltas."""
    norms = [np.linalg.norm(delta) for delta in delta_V.values()]

    if method == "mean":
        return np.mean(norms)
    elif method == "median":
        return np.median(norms)
    else:
        raise ValueError(f"Invalid method '{method}'.")


def clip_deltas(delta_V, clipping_threshold=None, method="median"):
    """Clip deltas based on a specified or calculated threshold."""
    if clipping_threshold is None:
        clipping_threshold = calculate_optimal_threshold(delta_V, method=method)

    for item_id, delta in delta_V.items():
        norm = np.linalg.norm(delta)
        if norm > clipping_threshold:
            delta_V[item_id] = (delta / norm) * clipping_threshold

    return delta_V, clipping_threshold


def get_noise_function(noise_type):
    """Factory function to return the appropriate noise generation function."""
    if noise_type == "gaussian":
        def gaussian_noise(sensitivity, epsilon, size, delta=1e-5):
            sigma = np.sqrt(2 * np.log(1.25 / delta)) * (sensitivity / epsilon)
            return np.random.normal(loc=0, scale=sigma, size=size)
        return gaussian_noise
    elif noise_type == "laplace":
        def laplace_noise(sensitivity, epsilon, size):
            scale = sensitivity / epsilon
            return np.random.laplace(loc=0, scale=scale, size=size)
        return laplace_noise
    else:
        raise ValueError("Invalid noise_type. Use 'gaussian' or 'laplace'.")


def apply_differential_privacy(delta_V, epsilon, sensitivity, noise_type="gaussian"):
    """Apply differential privacy to the deltas by adding noise."""
    result = copy.deepcopy(delta_V)
    noise_function = get_noise_function(noise_type)

    for item_id, delta in result.items():
        norm = np.linalg.norm(delta)
        noise = noise_function(sensitivity, epsilon, size=delta.shape)

        if norm > 0:
            delta /= norm
            delta += noise
            delta *= norm
        else:
            delta += noise

        result[item_id] = delta

    return result


def plot_delta_distributions(
    user_id, delta_norms_before, delta_norms_after, clipping_threshold=0.8
):
    """Plot the distribution of delta norms before and after differential privacy."""
    delta_norms_after_clipped = np.clip(delta_norms_after, 0, clipping_threshold)
    plt.figure(figsize=(12, 6))
    plt.hist(
        delta_norms_before,
        bins=50,
        alpha=0.7,
        label="Before DP Noise",
        color="blue",
        density=True,
    )
    plt.hist(
        delta_norms_after_clipped,
        bins=50,
        alpha=0.7,
        label="After DP Noise",
        color="red",
        density=True,
    )
    plt.title(
        f"{user_id}: Distribution of Delta Norms Before and After Differential Privacy Noise",
        fontsize=14,
    )
    plt.xlabel("Delta Norms", fontsize=12)
    plt.ylabel("Density", fontsize=12)
    plt.legend(fontsize=12)
    plt.grid(alpha=0.3)
    plt.show()


def plot_ratings_norm(user_id, sorted_item_ids, delta_norms_before, delta_norms_after):
    """
    Plot the norms of ratings deltas before and after differential privacy noise.

    Parameters:
        user_id (str): Identifier for the user whose data is being plotted.
        sorted_item_ids (list): List of sorted item IDs (x-axis).
        delta_norms_before (list): List of delta norms before DP.
        delta_norms_after (list): List of delta norms after DP.
    """
    # Convert to lists if needed
    sorted_item_ids = list(sorted_item_ids)
    sorted_norms_before = list(delta_norms_before)
    sorted_norms_after = list(delta_norms_after)

    # Filter out zeros for "Before DP"
    non_zero_ids_before = [
        item_id
        for item_id, norm in zip(sorted_item_ids, sorted_norms_before)
        if norm > 0
    ]
    non_zero_norms_before = [norm for norm in sorted_norms_before if norm > 0]
    non_zero_norms_after = [
        sorted_norms_after[i] for i, norm in enumerate(sorted_norms_before) if norm > 0
    ]

    # Visualization
    plt.figure(figsize=(15, 6))

    # Plot "Before DP" for non-zero values only
    plt.plot(
        non_zero_ids_before,
        non_zero_norms_before,
        label="Before DP (Non-zero)",
        marker="o",
        linestyle="-",
        alpha=0.7,
    )

    # Plot "After DP" for all values
    plt.plot(
        sorted_item_ids, sorted_norms_after, label="After DP", linestyle="--", alpha=0.7
    )

    plt.xlabel("Item IDs (Sorted)", fontsize=12)
    plt.ylabel("Norm of Delta", fontsize=12)
    plt.title(
        f"{user_id}: Norm of Ratings Deltas Before and After Differential Privacy Noise",
        fontsize=14,
    )
    plt.legend(fontsize=12)
    plt.grid(alpha=0.3)

    # Display fewer ticks to avoid clutter
    plt.xticks(
        sorted_item_ids[::50], rotation=45, fontsize=10
    )

    plt.show()
