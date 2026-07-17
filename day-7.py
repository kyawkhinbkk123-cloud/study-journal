# M2 Day 7 - Unsupervised: K-Means clustering (Feynman own build)

from sklearn.cluster import KMeans
import numpy as np

# Own data: study sessions as (minutes, score)
X = np.array([
    [30, 50], [40, 55], [35, 52],   # low group
    [90, 85], [80, 82], [95, 88],   # high group
    [60, 65], [55, 62],             # mid group
])

km = KMeans(n_clusters=3, random_state=0, n_init=10).fit(X)
print("cluster labels:", km.labels_)
print("centers:\n", km.cluster_centers_)

# RL link: clustering groups states (state-space discretization) - used in RL to simplify env
print("groups found:", len(km.cluster_centers_))
