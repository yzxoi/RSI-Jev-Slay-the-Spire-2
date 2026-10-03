# E138 — M3 Max profiling before RL device changes

Hypothesis: batched MPS kernels may be faster, but CPU engine/encoding/reset dominate the current 73,794-parameter pipeline. Do not infer end-to-end speedup from GPU kernel timing.

Fixed input: first 12 optimized episodes from each learner's update 1 in committed E133 training-v2; audit their trace/wire hashes and reconstruct the original encoder inputs. Fixed frozen E133 long-1701 weights. No new gameplay, gradients used for benchmarking only, no trained checkpoint or win-rate claim.

Compare CPU single-thread and available MPS, batches 1/8/32/128/512, three repeats of 30 forwards and 10 fixed PPO-like backward/Adam steps, five warmups. Larger batches repeat fixed real observations and are explicitly microbenchmarks. Include CPU padding, device transfer and synchronization; separately time Python encoding. Compare probabilities/value on identical frozen weights within atol 2e-4 /2e-3, finite loss/gradients. Retain errors, disable silent CPU fallback. Wall phase cap 10 minutes.

Decision: default per-action device changes require >=1.2x latency improvement including conversion and numeric parity. Batched MPS is eligible only in measured faster shapes; never claim existing collection throughput gains from batching not yet implemented. Use E133 measured work fractions to bound optimizer-only whole-training gains. No budget or policy promotion.

Command: `python3 scripts/profile_ppo_e138.py --output artifacts/runs/e138-profile-v1.json`

## Result v1

Tested SHA `ff8948e`; 24 source episodes, 452 reconstructed observations. All source trace/wire hashes passed. CPU/MPS frozen probabilities and values passed tolerance; all optimizer losses/gradients finite. No weight saved or gameplay performed.

| Batch | CPU forward ms | MPS forward ms | Forward speedup | Update speedup |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.094 | 2.085 | 0.05x | 0.13x |
| 8 | 0.165 | 2.246 | 0.07x | 0.11x |
| 32 | 0.333 | 2.682 | 0.12x | 0.16x |
| 128 | 1.732 | 3.218 | 0.54x | 0.39x |
| 512 | 9.931 | 6.493 | 1.53x | 1.21x |

Decision: do not move current single-state inference or minibatch-128 optimization to MPS. Batch512 shows 1.53x inference and 1.21x optimization speedups, but this is a microbenchmark; collection batching is not implemented. E133 optimizer is only0.855% of training+validation work, giving an infinite-optimizer-speed upper bound of1.0086x. Keep CPU default; revisit MPS for larger models or actual batch512 pipelines. Profiling took14.69s. This does not establish policy strength.
