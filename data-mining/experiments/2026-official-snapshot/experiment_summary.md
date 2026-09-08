# 2026 Official LA Collision Snapshot

This directory records a reproduction on a fresh Los Angeles Open Data download
on 2026-09-08. It is not a reconstruction of the original 2025 coursework
snapshot. The 123,840,942-byte source CSV remains outside the repository and
is neither copied nor versioned here.

## Dataset and preprocessing

| Measure | Result |
| --- | ---: |
| Raw records | 621,677 |
| Valid coordinate records | 614,812 |
| Retained after preprocessing | 614,812 |
| Dropped records | 6,865 (1.104%) |
| Parsed occurrence range | 2010-01-01 00:05 to 2025-03-08 11:10 |
| Preprocessing runtime | 3.288 s |
| Approximate process RSS while loading/preprocessing | 562.7 MB |

Required-field missingness in the raw snapshot: `Location` 0, `Date Occurred`
0, `Time Occurred` 0, `Victim Age` 88,194, `Victim Sex` 10,697, and `Victim
Descent` 11,648. Coordinate validation, not demographic missingness, drives the
observed row drop.

## Baseline review and final method

The untouched baseline used a six-dimensional DBSCAN distance: four standardized
grid features (`accident_count`, `avg_age_group`, `weekend_ratio`, `peak_hour`)
plus standardized grid latitude/longitude, with the coordinates weighted by
0.5. Its old default `eps=0.05` labeled all 1,314 grid cells as noise; values
above 0.5 were not available in the UI despite materially changing behaviour.

The final implementation defines DBSCAN as **grid-pattern clustering**, not
pure geographic hotspot detection. Its distance contains standardized
`accident_count` and `weekend_ratio`, plus standardized grid coordinates with
the existing 0.5 coordinate weight. `AgeGroupNum` and linear `peak_hour` are
retained for descriptive summaries but removed from the DBSCAN distance because
the former imposes an unjustified ordinal spacing and the latter treats 23:00
and 00:00 as far apart. The UI now labels epsilon honestly and exposes
0.10--1.20, with an exploratory balanced default of `grid_size=0.01`,
`eps=0.25`, and `min_samples=5`.

The final K-Means analysis is record-level and uses cyclical hour and weekday
encodings, median-imputed victim age plus an age-missing indicator, and one-hot
`Victim Sex` and `Victim Descent`. `Premise Description` is retained for
descriptive summaries but excluded from the distance space to avoid letting a
large one-hot block dominate Euclidean distance. It describes temporal and
demographic record patterns, not spatial groups. The supplied metrics are
full-data fit statistics; silhouette is explicitly a deterministic 20,000-record
sample (`np.random.default_rng(42).choice(..., replace=False)`). K=2 has the
highest sampled silhouette; larger K values provide finer exploratory
segmentation without a strong multi-cluster optimum.

Compare mode intentionally applies both DBSCAN and K-Means to the same
grid-level feature matrix. Its crosstab describes overlap of grid assignments;
it is not an agreement or quality score, and it is distinct from the main
record-level K-Means analysis.

## Reading the tables

- `final_grid_sweep.csv` is the final DBSCAN feature space at the balanced
  `eps=0.25`, `min_samples=5` setting.
- `final_dbscan_eps_sweep.csv` and `final_min_samples_sweep.csv` are final
  DBSCAN feature-space scans on the complete snapshot.
- `final_kmeans_sweep.csv` is a full-record K-Means scan; `sampled_silhouette` is
  not a full-dataset metric.

The experiments support algorithm-behaviour claims: fine grids retain more
local detail, low epsilon yields high noise, and high epsilon merges patterns.
They do not establish collision causes, policy interventions, or citywide
geographic risk rankings.

## Interface validation

The Streamlit interface was run against the full snapshot: 614,812 displayed
records, 1,314 grid cells, and 21 DBSCAN labels including noise at the balanced
setting. Plotly 7 removed the legacy Mapbox trace classes used by the coursework
interface. The maps were migrated to MapLibre `Scattermap`; the collision
intensity view uses count-scaled/color-coded grid points rather than claiming a
kernel density surface. Screenshots in `../../demo/` are captured from this
real-data Streamlit session.
