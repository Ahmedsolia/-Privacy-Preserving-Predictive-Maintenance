## Stage 1 — Data and Factory Specification

### Status

- **State:** Locked for Track A, skeleton for Track B
- **Living doc:** Edited as planning continues
- **Locked values:**
  - **Window length W = 30**
  - **RUL cap = 125**
  - **Default k = 2**
  - **Tau = 0.75**

### Objective

- Build reproducible factory splits and preprocessing
- Enforce local-only statistics
- Fix inputs before any model training

## Tracks and Scope

### Track A — Deep Track

- **Dataset:** NASA C-MAPSS
- **Role:** All sweeps and main claims
- **Subsets:** FD001, FD002, FD003, FD004

### Track B — Secondary Track

- **Dataset:** Microsoft Azure Predictive Maintenance
- **Role:** Error codes and maintenance actions for real graph
- **Status:** Skeleton only, locked before any Track B work
- **Graph role:** Rich demo source

## Factory Simulation

### Track A Keys

- **Key format:** Held-out FD, source FD, shard, seed
- **Example:** FD001 with seed 2 and k 3
- **Procedure per seed:**
  - Permute engine IDs within each FD
  - Split into k contiguous shards
  - Each shard is one client

### Client Count

- **Parameter k:** Sub-clients per FD
- **Default k = 2**
  - **Result:** 6 training clients
- **Sweep A, fragmentation, k = 1, 2, 3, 4**
  - **Result:** 3, 6, 9, 12 clients
  - **Total data:** Fixed at 460 engines
  - **Answers:** Effect of splitting fixed data into more pieces
- **Sweep B, factory scaling, fixed client size:**
  - **Pool:** The 12 clients from k = 4, equalized to 25 engines each
  - **Equalization:** Seeded subsample of FD002 shards from 65 down to 25 engines
  - **Composition:** Balanced at m over 3 shards per FD
  - **Take m = 3, 6, 9, 12** clients, giving 1, 2, 3, 4 shards per FD
  - **Answers:** Effect of adding more same-sized factories
- **Budgets at k = 4:**
  - **FD001:** 25 engines per client
  - **FD003:** 25 engines per client
  - **FD002:** 65 engines per client
- **Participation:** Full participation at every k
  - **Reason:** Total data is identical, so compute cost is flat
  - **Partial participation:** Separate experiment only, never mixed into the sweep

### Held-Out Design

- **Default held-out:** FD004
  - **Reason:** Tests composition
  - **Conditions covered by:** FD002
  - **Fault modes covered by:** FD003
- **Rotation:** Leave-one-FD-out
  - **Scope:** Main comparison only
  - **Setting:** Fixed k, default k = 2
  - **Other rotations:** Generic cross-factory claim only

### Heterogeneity Control

- **High heterogeneity arm:** Pure-FD clients
- **Low heterogeneity arm:** Mixed-FD clients
  - **Construction:** Round-robin interleave across FD001 to FD003
  - **Seeding:** Seeded and reproducible
- **Size confound:**
  - **Issue:** FD002 clients hold about 2.6x engines
  - **Primary sweep:** Natural sizes, report per-client N
  - **Heterogeneity comparison:** Size-equalized via seeded subsample

### Track B Keys

- **Unit:** Machine ID
- **Grouping:** By model
  - **m1:** 16 machines, 189 failures
  - **m2:** 17 machines, 168 failures
  - **m3:** 35 machines, 221 failures
  - **m4:** 32 machines, 183 failures
- **Evaluation:** Leave-one-model-out, all four rotations averaged
- **Risk noted:** Low machine diversity, not low event count

## Windows and Labels — Track A

### Window Construction

- **Length:**
  - **W = 30** cycles
- **Stride:** 1 during training
- **Train windows:** Include front-padded t < 30 windows
  - **Reason:** Train must see test-time pattern
- **Padding:** Front-pad with zeros
- **Mask channel:**
  - **Value 1:** Real cycle
  - **Value 0:** Padded cycle

### Short Engines

- **Counts verified:**
  - **FD001:** Minimum 31, none below 30
  - **FD002:** Minimum 21, 6 engines below 30
  - **FD003:** Minimum 38, none below 30
  - **FD004:** Minimum 19, 11 engines below 30
- **Rule:** Pad to 30, never drop

### RUL Targets

- **Train label:** RUL at window end
  - **Cap applied:** Minimum of true RUL and 125
- **Eval:** Single last window per test engine
  - **Target:** Same capped value
- **Convention:**
  - **Primary:** Capped at 125 for all methods
  - **Sensitivity:** Uncapped table for literature comparison

## Feature Schema — Track A

### Global Schema

- **Scope:** Track A only, Azure has separate schema
- **Total inputs:** 17
  - **Operating settings:** 2
    - **Kept:** op1 and op2
  - **Sensors kept:** 14
    - **List:** s2, s3, s4, s7, s8, s9, s11, s12, s13, s14, s15, s17, s20, s21
  - **Mask:** 1
- **Dropped globally:** 7 items
  - **List:** op3, s1, s5, s6, s10, s16, s18, s19
- **Arithmetic:** 21 minus 7 equals 14 sensors, plus 2 settings plus 1 mask equals 17
- **Constraint:** Identical for every client, required for aggregation
- **Guard:** Epsilon of 1e-8 on all z-scores

### Resolution Rule

- **Metric:** Per-cluster ratio of std divided by resolution
  - **Resolution meaning:** Most common positive gap between sorted unique values
  - **Why mode gap:** Smallest gap is fragile to float noise or one odd reading
  - **Drop condition:** Minimum ratio below 1.0 in any cluster
  - **Reason:** One noisy cluster is enough to corrupt per-cluster z-scoring
  - **Evaluated on:** Training FDs only, list fixed afterwards
- **Audit on FD002 with mode gap:**
  - **Dropped ratios:** s1 0.00, s5 0.00, s6 0.129, s10 0.00, s16 0.00, s18 0.00, s19 0.00
  - **Mode-gap check:** s6 0.129, s8 7.09, s13 7.07, s17 1.29, all unchanged vs min-gap
  - **Closest kept:** s17 at 1.29, s8 at 7.09, s13 at 7.07
- **Boundary note:**
  - **s6 on FD004:** Ratio 1.07, marginal pass
  - **s6 step:** Exactly 0.01, with only 2 unique values in FD001
  - **Status:** Judgment call, justified by quantization
- **Process:**
  - **Fixed once:** Before any rotation
  - **Source:** Public instrument-level statistics
  - **Limitation:** Pre-check touched FD004, stated explicitly

## Normalization

### Sensor Normalization

- **Scope:** Strictly local per factory
- **Method:** Z-score per client and condition cluster
- **Stats frozen:** Applied to validation and test without refit
- **Never pooled:** No cross-client statistics

### Operating Settings

- **Model inputs:** op1 and op2 only
- **Scaling:** Fixed physical constants, identical for all clients
  - **op1 range:** 0 to 42.1
    - **Context:** Altitude envelope covering all FDs
  - **op2 range:** 0 to 0.85
    - **Context:** Mach envelope covering all FDs
  - **op3 range:** 60 to 100
    - **Context:** Clustering only, not a model input
- **Why fixed:** Per-client scaling would make same condition look different
- **Leakage statement:** Physical constants, not fitted statistics

### Verified Ranges

- **FD001:** op1 within plus-minus 0.009, op2 within plus-minus 0.001
- **FD003:** Same tiny band as FD001
- **FD002 and FD004:** op1 0 to 42.008, op2 0 to 0.842, op3 60 to 100
- **Consequence:** FD001-range scaling would blow up FD002 inputs by 1000x, rejected

### op3 Decision

- **Clustering:** op3 retained in scaled form
- **Model input:** op3 dropped
- **Evidence:**
  - **Agreement score:** 1.00 between 2-feature and 3-feature clusterings
  - **op3 within clusters:** Constant at 100.0 in five clusters, 60.0 in one
  - **Conclusion:** op1 and op2 already determine op3, nothing lost

## Condition Clustering

### Algorithm

- **Method:** K-means on scaled ops
- **Input:** Scaled op1, op2, op3 with fixed constants above
- **Why scaled:** Raw op1 spans 0 to 42 and op3 spans 60 to 100, op2 would be invisible

### Cluster Count Rule

- **Candidates:** k equals 2 to 6
- **Metric:** Best silhouette score, denoted s-star
- **Threshold:**
  - **Tau = 0.75**
- **Decision:**
  - **If s-star below tau:** Use k = 1
  - **If s-star at or above tau:** Use argmax k
- **Scope:** One rule for every client, including mixed and held-out

### Shard Coverage Verified

- **Pure shards, k = 4, seeds 0, 1, 2:**
  - **Count:** 12 shards per seed, 36 total
  - **FD001:** 0.593 to 0.607, all 12 below tau
  - **FD003:** 0.596 to 0.606, all 12 below tau
  - **FD002:** 0.997 on all 12 shards, all above tau
- **Mixed-FD clients, seeds 100, 101:**
  - **k = 2:** 6 clients per seed, 12 total, 0.997 to 0.998, all above tau
  - **k = 4:** 12 clients per seed, 24 total, 0.997 to 0.998, all above tau
  - **Reason:** Every mixed client contains FD002 engines
- **FD004 shards, k = 4, seeds 200, 201:**
  - **Count:** 4 shards per seed, 8 total
  - **Result:** 0.997 on all 8 shards, all above tau
- **Corrected total:** 36 plus 12 plus 24 plus 8 equals 80 checks
  - **Prior error:** 52 was a miscount, corrected here
- **Margin:** Wide on both sides, no shard near tau
- **Caveat:** Tau set using FD002, same leakage note as drop list under FD002-held-out rotation

### Test-Time Assignment

- **Centroids:** Frozen from training
  - **Fitted on:** Client's own train ops only
- **Per cycle:** Nearest centroid in scaled op-space
  - **Distance:** Euclidean
- **Held-out FD:** Same rule with its own centroids
  - **Fitted on:** Its own train file only

### Held-Out Normalization Rule

- **Fit on:** Held-out train file only
- **Fit what:** K-means plus per-cluster sensor stats
- **Weights:** Zero gradient steps on held-out data
- **Eval on:** Held-out test file and RUL file
- **Principle:** Consistent with local-only statistics

## Validation Splits

### C-MAPSS

- **Unit:** By engine, never by window
  - **Reason:** Window split leaks same unit across splits
  - **Rejected:** Time-based within-unit split, biased to low RUL
- **Ratio:** 80 train versus 20 validation per client
- **Stratify by:** Trajectory length
- **Small-client note at k = 4:**
  - **Result:** About 20 train and 5 validation engines
  - **Rule:** Select hyperparameters at k = 2 only

### Azure

- **Method:** Time cutoff at last 20 percent of each machine's timeline
- **Purge gap:** Label horizon N plus feature window length
  - **Fixed N:** 24 hours, defines the task
  - **Longer horizons:** 48 and 72 hours are separate tasks, reported only if time allows
  - **Window length:** Selected from 24, 48, 72 hours on training-model validation, per rotation
  - **Reason:** Stops validation windows reusing train-period telemetry through feature windows

## Evaluation Matrix

### Method Rows

- **Local-only:** One model per sub-client
  - **Report split:** In-domain versus cross-domain separately
  - **Averaging:** Within FD first, then across FDs
- **Centralized without held-out:** Fair baseline
- **Federated Averaging:** Main federated method
- **Federated Proximal:** Regularized federated variant
  - **Parameter mu:** Selected per rotation on training validation

### Reference Rows

- **Local-only on held-out:** What a new factory has alone
- **Centralized with held-out:** Oracle upper bound
- **Label:** References, not methods

### Test Columns

- **Columns:** Test FD001, FD002, FD003, plus held-out FD
- **Source:** Test text plus RUL file per FD
- **Rule:** No method sees held-out train or test during training

### Metrics and Rigor

- **C-MAPSS metrics:**
  - **Primary:** Root Mean Squared Error and NASA score
- **Azure metrics:**
  - **Primary:** F1-score and PR-AUC
  - **Always report:** Positive-rate baseline
- **Seeds:** 10 or more
  - **Vary:** Partition, initialization, and shuffle
- **Correction:** Holm for multiple comparisons
- **Selection rule:** Never touch held-out test
- **Model selection:** Final round picked by pooled validation engines
  - **Pool source:** Training clients only
- **Convergence:** Log validation every round
  - **Purpose:** Show whether Federated Proximal and DP runs converged within 50 rounds

## Privacy Notes Affecting Stage 1

- **Unit protected:** One engine or one machine, not one window
  - **Reason:** One engine yields 100 to 300 overlapping windows
- **Batching implication:** Variable-length engines need per-engine handling
  - **Loss:** Mean over the engine's windows, equal weight per engine
  - **Step:** Clip per engine, then sum and add noise
- **Accounting:** RDP or PRV accountant stepped manually
  - **Inputs:** Noise sigma and sampling rate q
  - **Scope:** All local steps across all rounds
  - **Step formula:** Steps per client equal rounds times local epochs times ceiling of train engines over batch engines
- **Delta:** 1e-5
  - **Check:** Below 1 over N for smallest client with N = 25
- **Clip norm C:** From a fixed grid, never from private gradients
  - **Privacy note:** Tuning C and sigma on private data costs privacy that is not accounted for, stated as limitation
  - **Extended:** Validation-based round and hyperparameter selection also touches private data and is covered by the same limitation
- **Noise policy:** Fix sigma globally, report per-client epsilon
  - **Headline:** Maximum epsilon across clients, the least private one
  - **Sampling rate q:** 8 divided by train engines per client
    - **Denominator rule:** Post 80/20 split train count, not shard count
    - **At k = 2:** 0.20 for FD001-like with 40 train engines, about 0.077 for FD002-like with 104 train engines
    - **At k = 4:** 0.40 for FD001-like with 20 train engines, about 0.154 for FD002-like with 52 train engines
    - **Correction note:** Earlier values used shard counts and understated q, hence understated epsilon; corrected here
- **Epsilon sweep:** 4, 8, 16, and infinity
  - **Mapping:** Each value is a target for the maximum-epsilon client
  - **Procedure:** For each target, solve sigma with the accountant by binary search, then report every client's resulting epsilon
  - **Infinity defined as two arms:** Clip-only versus clean training, separating clip cost from noise cost
  - **Applies to:** Federated Averaging full sweep, Federated Proximal plus DP at 4.7 only
  - **Attacks:** Membership inference on engines is primary, gradient inversion on windows is optional
  - **Expectation:** Steep curve, epsilon 1 likely collapses
- **Import status:** Unverified here, first Stage 2 task in training env

## Azure Skeleton — To Lock Before Track B

- **Telemetry window:** Selected from 24, 48, 72 hours on training-model validation, per rotation
- **Lag features:** From errors and maintenance
  - **Errors:** 5 types
  - **Maintenance:** 4 components
- **Static features:** Age only
  - **Removed:** Model one-hot
  - **Reason:** Unseen category under leave-one-model-out, constant within client
- **Leakage rule:** Every lag feature uses records at or before window end only
  - **Note:** Failures coincide with unscheduled replacements in this dataset
  - **Required test:** Assert no feature touches rows inside the label horizon
- **Label:** Failure within N hours with N fixed at 24, defines the task
- **Imbalance:** Focal loss first, fallbacks are weighted loss and downsampling
- **Graph and model choice:** After Stage 2

## Limitations Recorded

- **Schema leakage:** Drop list and tau touched FD002 and FD004 during design
- **Size confound:** Isolated only in heterogeneity arm
- **Composition claim:** Applies to FD004-held-out rotation only
- **Opacus version:** Pinned later in training env
- **DP scope:** Privacy-utility results come from one configuration only
  - **Setting:** Held-out FD004 with k = 2
  - **Rule:** State this alongside the main results

## Stage 2 Handoff — Concrete Starting Configs

### Sequence Models

- **Primary:** Long Short-Term Memory network
  - **Hidden size:** 64
  - **Layers:** 2
  - **Normalization:** LayerNorm, never BatchNorm
- **Fallback order:**
  - **First:** Per-engine loop if vmap over LSTM fails
  - **Second:** Gated Recurrent Unit
- **Variant:** Transformer, sized to match LSTM parameter count

### Optimization

- **Optimizer:** Adam
  - **Learning rate:** 0.001
  - **Batch, non-DP:** 32 windows
  - **Batch, DP:** 8 engines
  - **State:** Stateless clients, optimizer state resets each round
  - **DP check:** Verify DP-Adam rescaling behaves with clipping before the epsilon sweep
- **Local work:** 2 epochs per round
- **Rounds:** 50
- **Participation:** Full participation at every k
  - **Partial participation:** Separate experiment only

### Federation

- **Aggregation weight:** Number of engines, not windows
  - **Reason:** Matches the engine-level privacy unit
- **FedProx grid:**
  - **Mu values:** 0, 0.01, 0.1, 1.0
  - **Selection:** Per rotation on training validation

### Accountant Check

- **Compare:** RDP versus PRV on same sigma, rate, and steps
- **Monotonicity:**
  - **Epsilon rises with:** Steps and sampling rate
  - **Epsilon falls with:** Noise sigma
- **No reliance:** On a single known configuration
