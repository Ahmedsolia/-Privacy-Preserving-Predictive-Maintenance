## Implementation Plan — All Stages

### How to Use This File

- **Order:** Stages run top to bottom, no skipping
- **Exception:** Build and test the Stage 1 pipeline for FD001 to FD003 first, running Stage 1 checks 1, 3, and 4 on those FDs, then run Stage 0, then complete the remaining Stage 1 work
  - **Why:** Top to bottom with no skipping contradicts Stage 0 reusing Stage 1 code, so without an explicit exception either the gate rule gets broken or throwaway code gets written
- **Gate rule:** A stage is done only when every sanity check passes
- **On failure:** Fix and re-run the check, never carry failures forward
- **Detail source:** Stage-1-Spec.md holds the locked Stage 1 numbers

## Infrastructure — Before Stage 0

### Objective

- **Goal:** Every run reproducible from disk with no manual steps

### Steps

- **Config system:** One YAML per experiment
  - **Contains:** Seeds, k, rotation, method, mu, epsilon target, rounds
  - **Rule:** No hardcoded constants in code, config is the record
- **Seed handling:** Single master seed fans out deterministically
  - **Streams:** Partition, initialization, and shuffling drawn separately
  - **Logged:** All three sub-seeds per run
- **Pinned versions:** Torch, Opacus, scikit-learn, NumPy recorded at first run
  - **Stored:** Versions file alongside logs
- **Run logging:** Every run writes JSON lines to disk
  - **Contains:** Config hash, per-round validation, final metrics, timing, epsilon report
- **Table script:** One script regenerates every table from logs only
  - **Rule:** No hand-copied numbers in documentation

### Automated Test Suite

- **Runner:** Single command runs all tests, fails the stage on any red
- **Tests:**
  - **Padding:** All windows are length 30 with correct mask zeros on pads
  - **Split overlap:** Zero shared engines or machines across train, validation, and test
  - **Stats locality:** No shared normalization stats across clients, constants match the published set
  - **Rate values:** q matches train-engine denominators per client type
  - **Schema:** Identical feature count on every client batch
  - **Leakage:** No Track B feature reads rows inside the label horizon
- **Rule:** Sanity checks run as these tests, not as manual inspection

### Sanity Check

- **Check 1:** Rerun reproduces logs
  - **Pass:** Same config hash gives identical metrics within tolerance
  - **On fail:** Fix nondeterminism before any stage starts
- **Check 2:** Tables regenerate from logs
  - **Pass:** Script output matches reported tables cell for cell
  - **On fail:** Fix the script, never edit tables by hand

## Stage 0 — Thin Slice

### Objective

- **Goal:** Prove end-to-end integration before deep work
- **Ordering:** Build the Stage 1 pipeline for FD001 to FD003 first, Stage 0 reuses it
  - **Rule:** No throwaway pipeline, the slice runs on production code paths

### Steps

- **Data:** FD001 to FD003 through the Stage 1 pipeline, default splits
- **Model:** Long Short-Term Memory network, small config
- **Learning:** Federated Averaging, few rounds
- **Knowledge:** Small graph plus tiny Azure lookup
- **Explanation:** One retrieval-grounded explanation

### Outputs

- **Trained global model:** Few rounds, no tuning claims
- **One explanation:** With cited facts
- **Integration log:** Every interface exercised once

### Sanity Check

- **Check 1:** Training loss decreases on every client
  - **Pass:** Downward trend, no NaN values
  - **On fail:** Inspect windowing and normalization stats
- **Check 2:** Aggregation runs without shape errors
  - **Pass:** Identical 17-feature schema on all clients
  - **On fail:** Re-audit the global drop list
- **Check 3:** Explanation cites resolve
  - **Pass:** Every citation matches a fact ID or model field
  - **On fail:** Fix the JSON claim format

## Stage 1 — Data and Factories

### Objective

- **Goal:** Reproducible splits and local-only preprocessing

### Steps — Track A

- **Split:** Factory key with held-out FD, source FD, shard, seed
- **Windows:** Length 30, stride 1, front-pad plus mask
- **Labels:** RUL capped at 125, last window per test engine
- **Schema:** Global 14-sensor list, 17 total inputs
- **Normalization:** Per-client per-cluster z-scores, fixed physical constants
- **Clustering:** Silhouette rule with tau 0.75

### Steps — Track B

- **Split:** Factory key with held-out model, model, seed
- **Evaluation:** Leave-one-model-out, all four rotations
- **Cutoff:** Last 20 percent of each machine's timeline is test, rest is train and validation
- **Task definition:** Failure within N hours with N fixed at 24
  - **Longer horizons:** 48 and 72 hours are separate tasks, reported only if time allows
  - **Why fixed:** N changes the labels, so scores across different N are not comparable and N cannot be selected on them
- **Window length:** Chosen from 24, 48, 72 hours on training-model validation, per rotation
  - **Why valid:** Window length does not change labels, so selection on validation is legitimate
- **Features:** Telemetry plus error and maintenance lag features plus age
- **Removed:** Model one-hot, unseen under held-out and constant in-client
- **Leakage rule:** Lag features from records at or before window end only
- **Purge gap:** Horizon N plus feature window length
- **Imbalance:** First attempt is focal loss
  - **Alpha:** 0.75 positive, 0.25 negative
  - **Gamma:** 2.0

### Outputs

- **Track A:** Client datasets for all k settings, frozen stats bundles, engine split manifest
- **Track B:** Per-model client datasets, feature manifest, leakage test result
  - **Leakage test:** Asserts no feature touches rows inside the label horizon

### Sanity Check

- **Check 1:** No unit appears in two splits
  - **Pass:** Zero overlap between train, validation, and test engine lists on Track A and machine lists on Track B
  - **On fail:** Rebuild splits from engine or machine IDs
- **Check 2:** Held-out factory contributes zero gradients
  - **Pass:** Held-out FD engines and held-out-model machines absent from all training batches
  - **On fail:** Audit the data loader filters on both tracks
- **Check 3:** Stats are local-only
  - **Pass:** No shared means across clients, constants match the published set
  - **On fail:** Refit stats per client
- **Check 4:** Short engines handled
  - **Pass:** All 17 engines under 30 cycles padded with mask zero
  - **On fail:** Fix the padding path for train and test
- **Check 5:** Shard count and train counts match plan
  - **Pass:** 3, 6, 9, 12 clients for k equals 1 to 4, Sweep B balanced at m over 3 per FD
  - **Pass:** Train engines per client type read 40 and 104 at k = 2, 20 and 52 at k = 4
  - **Why:** Stage 4 sampling rates derive from these counts, wrong counts give a wrong epsilon with no error raised
- **Check 6:** Track B leakage test passes
  - **Pass:** Assert holds on every client, no feature reads inside the horizon
  - **On fail:** Rebuild lag features with strict cutoff at window end

## Stage 2 — Baselines and Models

### Objective

- **Goal:** Non-federated reference numbers plus verified privacy tooling

### Steps — Track A Models

- **Task 0:** Accountant verification in training env
  - **Import:** RDPAccountant, required
  - **Second import:** PRVAccountant, best effort
  - **Compare:** Both on identical sigma, rate, and steps
  - **Assert:** Epsilon rises with steps and rate, falls with sigma
  - **Record:** Torch and Opacus versions in the spec
- **RUL loss:** Mean Squared Error on RUL targets capped at 125
- **Prediction handling:** Raw model outputs used as-is in every evaluation
  - **Rule:** No clipping or post-processing of predictions anywhere
- **Primary evaluation:** RMSE against capped ground-truth RUL
- **Sensitivity evaluation:** Separate RMSE table against uncapped ground-truth RUL
  - **Literature comparison:** Uncapped table only
- **Models:**
  - **Primary:** Long Short-Term Memory network
    - **Hidden size:** 64
    - **Layers:** 2
    - **Normalization:** LayerNorm only
  - **Variant:** Transformer, explicit config below
    - **Layers:** 2
    - **Heads:** 4 attention heads
    - **Width:** d_model equals 64
    - **Masking:** Padding mask blocks padded steps in attention and in the readout
    - **Readout:** Last valid time step
    - **Size match:** Record both models' trainable parameter counts, adjust feed-forward width until within 10 percent of the LSTM count
  - **Fallbacks:** Per-engine loop first, Gated Recurrent Unit second
- **Training:**
  - **Optimizer:** Adam with learning rate 0.001
  - **State:** Stateless, resets each round
  - **Batch non-DP:** 32 windows
  - **Selection:** Pooled training-client validation only
- **Fair tuning:** Comparable budget for every compared method
  - **Covers:** Local-only, Centralized, and all federated methods
  - **Goal:** Comparable effort, not identical values or spaces
  - **Document per method:** Search space, configurations evaluated, training budget
  - **Freeze:** Tuning config frozen with version hash before final experiments
  - **Track B:** Selection per rotation on permitted training-model validation
  - **Forbidden:** Test results never select hyperparameters or models
- **Mean-RUL baseline:** Mean of permitted training targets per training setup
  - **Centralized gate:** Beats its baseline on all test columns, averaged over at least 3 seeds, else investigate before proceeding
  - **Local-only gate:** Beats its baseline on its own in-domain FD test set, averaged over at least 3 seeds
  - **No gate:** Local-only on unseen FDs, poor scores there are analyzed, not auto-failed
- **FD001 literature reference:** Non-gating comparison for the Centralized LSTM on FD001
  - **Sources:** 2 to 3 published LSTM studies on C-MAPSS FD001, verified metrics with citations
  - **Protocol notes:** Capping, preprocessing, windowing, architecture, and metrics differences explained
  - **Rules:** No invented values, no pass or fail threshold, pending if not yet verified

### Steps — Track B Baselines

- **Models:** Same architectures, Azure feature schema
- **Local-only:** One model per model-client, leave-one-model-out
- **Centralized:** Pooled training models, oracle with held-out included
- **Imbalance:** Focal loss first, fallbacks are weighted loss and downsampling
- **Metric:** Average Precision (AP), documented if the implementation convention differs
- **Baseline:** Positive-class prevalence from the exact held-out post-cutoff test windows used for AP, reported beside AP per rotation
- **Uncertainty:** Machine-level bootstrap, resampling machines not windows
  - **Document:** Replicate count, resampling unit, confidence-interval method
- **Leakage audit:** Triggered by suspiciously high or implausible AP, high AP alone is not proof of leakage
  - **Checks:** Future data in features, label leakage, maintenance or error misuse, temporal split violations, preprocessing leakage, purge-gap violations
  - **Ablation:** Telemetry only, error-log only, maintenance-record only, using existing feature definitions
  - **Flag rule:** One group near full-model AP triggers investigation, treated as diagnostic signal only

### Outputs

- **Track A:** Local-only table split in-domain and cross-domain, both centralized tables
- **Track A extras:** Mean-RUL baseline table, capped RMSE primary plus uncapped RMSE sensitivity, parameter counts for both models
- **Track A reference:** FD001 literature comparison, marked pending until verified
- **Track B:** Local-only and centralized tables per rotation with AP, prevalence baseline, and bootstrap intervals, averaged over all four
- **Timing:** One-round cost for DP and non-DP paths, feeds the compute budget

### Sanity Check

- **Check 1:** Task 0 passes in the training env
  - **Pass:** Imports work, monotonicity asserts hold
  - **On fail:** No DP runs start, fix the environment first
- **Check 2:** Centralized beats local-only cross-domain
  - **Pass:** Pooled training wins off its own FD
  - **On fail:** Suspect label leakage or broken validation
- **Check 3:** Mean-RUL gates hold
  - **Pass:** Centralized beats its baseline on all test columns over at least 3 seeds, local-only beats its baseline in-domain over at least 3 seeds
  - **On fail:** Investigate before proceeding, except local-only off-domain which is analyzed not failed
- **Check 3:** Oracle beats fair baseline
  - **Pass:** Centralized with held-out above centralized without it
  - **On fail:** Held-out plumbing is wrong
- **Check 4:** Timing recorded
  - **Pass:** Seconds per round and peak memory logged for both paths
  - **On fail:** Measure before committing to the full grid
- **Check 5:** Track B uncertainty and audit documented
  - **Pass:** Bootstrap procedure with replicates and interval method recorded, leakage audit filed for any flagged AP
  - **On fail:** AP numbers ship without intervals, which is not allowed

## Stage 3 — Federated Learning

### Objective

- **Goal:** Federated comparison with heterogeneity and scale answered separately

### Steps

- **Methods:**
  - **Method A:** Federated Averaging
  - **Method B:** Federated Proximal
    - **Mu grid:** 0, 0.01, 0.1, 1.0, selected per rotation
- **Weighting:** By engine count, never by window count
- **Schedule:**
  - **Local work:** 2 epochs per round
  - **Rounds:** 50 with per-round validation logging
  - **Participation:** Full at every k
- **Sweeps:**
  - **Sweep A:** k equals 1 to 4, fixed data, fragmentation question
  - **Sweep B:** m equals 3, 6, 9, 12 from equalized pool, scaling question
  - **Heterogeneity arm:** Pure-FD versus mixed-FD at k equals 2
    - **Pure:** Shards from one FD, high heterogeneity
    - **Mixed:** Round-robin interleave, low heterogeneity
    - **Matched:** Same engine pool and same client data sizes in both arms, only the mixing pattern varies
    - **Question:** Effect of heterogeneity at fixed count and size
  - **Rotation:** Leave-one-FD-out at fixed k for the main table
- **Track B FL:** Federated Averaging versus Federated Proximal per rotation
  - **Scope:** Core comparison only, full sweeps stay on Track A
  - **Aggregation:** By machine count, consistent with Track A

### Outputs

- **Main table:** Both methods plus baselines on all test columns
- **Sweep curves:** Fragmentation and scaling plotted separately
- **Heterogeneity table:** Pure versus mixed at fixed k with sizes reported
- **Track B table:** Core comparison averaged over all four rotations
- **Convergence logs:** Validation per round for every arm

### Sanity Check

- **Check 1:** Participation is full in both sweeps
  - **Pass:** Client count per round equals total clients
  - **On fail:** Results confound participation with count, rerun
- **Check 2:** Sweep B pool is equal and balanced
  - **Pass:** 25 engines per client, m over 3 shards per FD
  - **On fail:** Rebuild the pool with subsampling
- **Check 3:** Heterogeneity arm is isolated
  - **Pass:** k equals 2 with the same engine pool and matched client sizes in both arms, only mixing differs, sizes reported
  - **On fail:** Equalize pool and sizes before any heterogeneity claim
- **Check 4:** Convergence budget is fair
  - **Pass:** Same pre-specified round budget and extension rule for all methods in a comparison, per-round validation logged for every arm
  - **Unclear:** If convergence is still unclear at the maximum budget, report non-convergence as a limitation, never extend one arm alone

## Stage 4 — Privacy

### Objective

- **Goal:** Measured privacy-utility tradeoff plus attack evidence

### Steps

- **Unit:** One engine or machine, mean loss over its windows
- **Mechanism:** Per-engine clip, sum, add noise
- **Scope cap:** Held-out FD004 with k = 2 only
- **Applies to:** Federated Averaging, full epsilon sweep
  - **Second arm:** Federated Proximal plus DP at epsilon 4.7 only, documents the interaction
- **Step formula:** Accountant steps per client equal rounds times steps per round
  - **Steps per round:** Local epochs times ceiling of train engines over batch engines
  - **Example at k = 2:** FD001-like client with 40 train engines runs 2 times ceiling of 40 over 8, or 10 steps per round
- **Clip grid:** Fixed values including 3.0, never from private gradients
- **Sigma solving:** Binary search per epsilon target on the maximum-epsilon client
  - **Targets:** 4, 8, 16, plus no-noise reference
  - **Epsilon infinity defined as two arms:**
    - **Clip-only arm:** Clipping active, no noise added
    - **Clean arm:** No clipping and no noise, standard training
    - **Purpose:** Separates the cost of clipping from the cost of noise
  - **Report:** Every client's resulting epsilon
- **Secure aggregation:** Design discussion with threshold scheme as reference
- **Attacks:**
  - **Primary:** Membership inference on engines
    - **Reason:** C-MAPSS has no process parameters to reconstruct, so the paper's reconstruction target does not exist here
    - **Metric:** Attack success rate near 50 percent means protected
  - **Optional:** Gradient inversion on input windows
    - **Status:** Best effort, reported if it runs

### Outputs

- **Tradeoff curve:** Epsilon versus RMSE and NASA score, both infinity arms plotted
- **Attack table:** Membership success rate per setting, inversion error only if the optional arm runs
- **Leakage note:** Updates, shared schema, and central-LLM variant discussed

### Sanity Check

- **Check 1:** Rates use train-engine denominators
  - **Pass:** q equals 0.20 and 0.077 at k = 2, 0.40 and 0.154 at k = 4 for the two client types
  - **On fail:** Epsilon is optimistic, recompute before reporting
- **Check 2:** Sigma solved, not copied
  - **Pass:** Binary search trace exists per target
  - **On fail:** No epsilon claim is valid
- **Check 3:** Scope stated with results
  - **Pass:** Every privacy figure labeled with its single configuration
  - **On fail:** Add the label, single-config results must not read as general
- **Check 4:** Unaccounted costs disclosed
  - **Pass:** Clip tuning, sigma tuning, and validation selection listed as limitation
  - **On fail:** Extend the limitation text

## Stage 5 — Knowledge Graph and Explanations

### Objective

- **Goal:** Grounded explanations a maintenance engineer can act on

### Steps

- **Ontology:** Shared schema agreed once
  - **Entities:** Machine, component, sensor, error code, failure mode, action
- **Local graphs:** Built per factory from own data only
- **Enrichment:** Sensor-to-fault relations for C-MAPSS, required since it has no logs
- **Azure role:** Rich demo with errors and maintenance chains, only track with failure-mode explanations
- **Explained model:** Final Federated Averaging global model at the default config
  - **Inputs explained:** Held-out test windows with predicted RUL
- **Local model:** Llama 3.1 8B Instruct
  - **Quantization fallback:** Q4 variant if VRAM is under 16 GB
  - **Context budget:** Retrieved facts capped at 2000 tokens plus window stats
  - **Pin rule:** Exact weights and quantization recorded at Stage 5 kickoff after the hardware check
- **C-MAPSS limit:** No per-engine fault-mode labels exist, so no failure-mode claims there
  - **Allowed facts:** Sensor-deviation facts only on Track A
- **Generation:** Retrieval over graph facts plus model output
  - **Default location:** Local open-weights model per factory
- **Format:** JSON claims, each citing a fact ID or model field

### Outputs

- **Graph dumps:** Per factory with triple counts
- **Explanation set:** Grounded and ungrounded variants per prediction
- **Template baseline:** Same facts rendered without the model

### Sanity Check

- **Check 1:** Facts stay local
  - **Pass:** No raw triples leave the factory in the local-LLM path
  - **On fail:** Redesign the retrieval boundary before any demo
- **Check 2:** Citations verify automatically
  - **Pass:** 100 percent of cites resolve, unmatched count equals hallucination count
  - **On fail:** Fix generation format, not the verifier
- **Check 3:** Template baseline exists
  - **Pass:** Every LLM explanation has a same-facts template twin
  - **On fail:** The with-versus-without comparison is invalid
- **Check 4:** C-MAPSS enrichment present
  - **Pass:** Sensor-to-fault relations documented with sources
  - **On fail:** C-MAPSS explanations have nothing to ground on

## Stage 6 — Evaluation and Write-Up

### Objective

- **Goal:** Generalization claim with ablations and honest limits

### Steps

- **Generalization:** Held-out drop versus oracle, fair baseline alongside
- **Ablations:** Without graph, without privacy, without LLM grounding, without federation
- **Rigor:**
  - **Main table:** 10 or more seeds, carries the significance claims
  - **Sweeps and ablations:** 3 to 5 seeds, trends only, no significance claims
  - **Correction:** Holm across method pairs and tracks, main table only
- **Metrics:**
  - **C-MAPSS:** Root Mean Squared Error and NASA score, uncapped sensitivity table included
  - **Azure:** F1-score and PR-AUC with positive-rate baselines
  - **Cost:** Communication bytes per round times rounds

### Outputs

- **Result tables:** Means with deviations plus significance statements
- **Ablation table:** Each removal isolated to one change
- **Limitations section:** Every recorded caveat restated with scope

### Sanity Check

- **Check 1:** Seeds and correction complete
  - **Pass:** 10 or more paired seeds on the main table, Holm applied, uncapped table present
  - **On fail:** No significance claim is made
- **Check 2:** Ablations are single-change
  - **Pass:** Each row differs from main by exactly one component
  - **On fail:** Redesign the table, stacked removals prove nothing
- **Check 3:** Claims match scope
  - **Pass:** Composition claimed only for FD004 rotation, DP claims labeled single-config
  - **On fail:** Narrow the wording to what was run
- **Check 4:** Human spot-check done
  - **Pass:** Sample of explanations hand-reviewed for faithfulness
  - **On fail:** Report automatic scores only, labeled as such

## Compute Budget

### Seed Allocation

- **Main table:** 10 or more seeds
  - **Reason:** Only table carrying significance claims
- **Sweeps and ablations:** 3 to 5 seeds
  - **Reason:** Trends only, keeps the grid affordable
- **DP arms:** 3 to 5 seeds at capped single configuration

### Runtime Estimates

- **Basis:** One-round timing from Stage 2, scaled by rounds times clients times seeds
- **Record per stage:** Estimated hours before launch, actual hours after
- **DP multiplier:** Logged separately, per-engine loops cost more than batched windows

### Cut Rule

- **Trigger:** Any stage projected beyond its time box
- **Order of cuts:**
  - **First:** Drop the outermost sweep points, keep default k = 2 and m extremes
  - **Second:** Reduce Transformer arms, keep the LSTM primary
  - **Never cut:** Main table seeds, held-out coverage, leakage tests
- **Gate:** No full-grid launch without a written estimate and a cut plan
