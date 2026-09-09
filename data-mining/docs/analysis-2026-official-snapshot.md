# Analysis of the 2026 LA Traffic Collision Snapshot

## 1. Dataset and Validation

The analysis uses a fresh 2026-09-08 download of Los Angeles Open Data's
*Traffic Collision Data from 2010 to Present* dataset. The CSV contains 621,677
raw records. Current preprocessing retains 614,812 records, dropping 6,865
(1.10%) after coordinate parsing, Los Angeles boundary validation, and valid
occurrence-date/time requirements. The retained occurrence dates span
2010-01-01 to 2025-03-08.

Coordinate strings are parsed into latitude and longitude and restricted to the
configured LA bounds. Invalid dates or clock times are removed. Victim age is
imputed only where a downstream feature requires it: the grid summaries use
age groups, and record-level K-Means uses median age plus a separate missing-age
indicator. Missing sex and descent are retained as \`Unknown\` categories for
K-Means. This fresh snapshot is not claimed to be identical to the original
2025 coursework dataset snapshot.

## 2. Analysis Design

### DBSCAN Grid Patterns

The DBSCAN analysis unit is a spatial grid cell. For the final model, the
distance space contains standardized \`accident_count\` and \`weekend_ratio\`,
combined with standardized grid latitude and longitude multiplied by 0.5.
Grid cells still retain average victim age, modal hour, and age-group fields for
descriptive summaries, but those fields are not part of the DBSCAN distance.

\`eps\` is a distance in this standardized mixed-feature space. It is not a
distance in kilometres or geographic degrees. The interface default uses a
0.01-degree grid, \`eps=0.25\`, and \`min_samples=5\` as a balanced exploratory
setting, not an optimal parameter set.

### K-Means Record Patterns

The K-Means analysis unit is an individual collision record. Hour and weekday
are encoded as sine/cosine pairs so recurring boundaries remain adjacent.
Victim age is median-imputed and paired with an age-missing indicator. Victim
sex and victim descent are one-hot encoded; \`Premise Description\` is excluded
from the distance space to avoid a large sparse categorical block dominating
Euclidean distance.

The final matrix has 34 columns: six numeric/cyclical columns (\`HourSin\`,
\`HourCos\`, \`WeekdaySin\`, \`WeekdayCos\`, \`Victim Age\`, and \`AgeMissing\`), seven
one-hot victim-sex columns, and 21 one-hot victim-descent columns. The six
numeric/cyclical columns are transformed by \`StandardScaler\`. The one-hot
columns remain binary and are not re-standardized. This is a reasonable
weighting design: a category's contribution is binary rather than inflated by
standardizing rare categories.

K-Means record patterns are not spatial clusters, although their labels can be
plotted geographically. The map uses a deterministic 5,000-record display
sample; clustering itself uses all uploaded valid records.

### Compare Grid Clustering

Compare mode applies DBSCAN and K-Means to the same grid-level matrix of
\`accident_count\` and \`weekend_ratio\`. Its crosstab is descriptive overlap, not
an accuracy, agreement, or validation metric.

## 3. DBSCAN Parameter Sensitivity

### Epsilon

All values below use the 0.01-degree grid and \`min_samples=5\`.

| eps | Clusters | Noise cells | Noise |
| ---: | ---: | ---: | ---: |
| 0.10 | 1 | 1,309 | 99.62% |
| 0.15 | 13 | 1,233 | 93.84% |
| 0.20 | 39 | 760 | 57.84% |
| 0.25 | 20 | 376 | 28.61% |
| 0.30 | 12 | 198 | 15.07% |
| 0.40 | 6 | 67 | 5.10% |
| 0.50 | 2 | 30 | 2.28% |

Low epsilon values produce extreme fragmentation and high noise. The middle
range produces multiple grid patterns. At higher values, patterns merge into a
few large groups with low noise. \`eps=0.25\` is therefore a balanced exploratory
default, not an optimum.

### Minimum Samples

At \`eps=0.25\` and grid size 0.01, increasing \`min_samples\` imposes a stricter
local-density requirement and generally increases noise.

| min_samples | Clusters | Noise cells | Noise |
| ---: | ---: | ---: | ---: |
| 3 | 36 | 194 | 14.76% |
| 5 | 20 | 376 | 28.61% |
| 10 | 11 | 824 | 62.71% |
| 15 | 3 | 1,211 | 92.16% |
| 20 | 1 | 1,272 | 96.80% |

Cluster count need not be monotonic under this change.

### Grid Resolution

These results use \`eps=0.25\` and \`min_samples=5\`.

| Grid size (degrees) | Grid cells | Clusters | Noise cells | Noise |
| ---: | ---: | ---: | ---: | ---: |
| 0.005 | 4,339 | 19 | 424 | 9.77% |
| 0.010 | 1,314 | 20 | 376 | 28.61% |
| 0.020 | 401 | 14 | 261 | 65.09% |
| 0.030 | 210 | 3 | 194 | 92.38% |

Changing grid size changes both spatial resolution and the number of
observations supplied to DBSCAN. Under fixed clustering parameters, coarser
grids produced fewer cells and materially different noise and cluster behavior.

## 4. K-Means Model Exploration

The K-Means sweep fits the full 614,812-record matrix. Silhouette is calculated
on a deterministic 20,000-record sample selected without replacement by
\`np.random.default_rng(42)\`.

| K | Sampled silhouette | Smallest group | Largest group |
| ---: | ---: | ---: | ---: |
| 2 | 0.2320 | 86,983 | 527,829 |
| 4 | 0.1488 | 86,983 | 192,398 |
| 6 | 0.1438 | 71,593 | 128,894 |
| 8 | 0.1419 | 50,556 | 90,672 |
| 10 | 0.1495 | 43,147 | 77,863 |
| 12 | 0.1430 | 32,885 | 69,937 |
| 16 | 0.1442 | 16,096 | 58,641 |
| 20 | 0.1438 | 12,773 | 43,839 |

K=2 has the highest sampled silhouette. Larger K values provide finer temporal
and demographic segmentation, but the sweep does not identify a strong,
nontrivial multi-cluster optimum. K=4 is used in the record-pattern screenshot
because it provides a readable exploratory multi-group view; it is not called
optimal.

## 5. What the Data Supports

### Supported Findings

- Collision records are spatially concentrated rather than uniformly distributed
  across the displayed LA map.
- DBSCAN output is highly sensitive to \`eps\` and \`min_samples\`.
- Grid resolution materially changes the grid-pattern representation.
- K-Means provides progressively finer temporal and demographic segmentation as
  K increases.
- The parameter sweeps do not justify a unique optimal multi-cluster solution.

### Exploratory Observations

- The DBSCAN maps show broad concentration patterns in the displayed urban area.
- DBSCAN grid-pattern groups have different descriptive weekend-ratio profiles.
- Record-pattern groups have different descriptive temporal and demographic
  compositions.

### What Should Not Be Claimed

This analysis does not establish causal explanations of collisions, neighborhood
safety rankings, predictive risk scores, policy recommendations, optimal
DBSCAN parameters, or exact reproduction of the 2025 coursework results.

## 6. Reproducibility

The lossless raw-data archive is stored at
\`data/archive/Traffic_Collision_Data_from_2010_to_Present_2026-09-08.zip\`.
Final tables are in \`experiments/2026-official-snapshot/\`; the four verified
Streamlit captures are in \`demo/\`; the 13-row synthetic fixture is in
\`examples/sample_collisions.csv\`; and regression tests are in \`tests/\`.
The Streamlit interface processes uploaded CSV files and renders both analysis
paths against the current implementation.

## 7. Archived 2025 Coursework Outputs

The PNG files under \`DemoPics/\` are preserved historical coursework outputs.
They are not treated as reproduced evidence for the 2026 snapshot.
