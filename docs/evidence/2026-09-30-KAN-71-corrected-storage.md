# KAN-71 corrected PostgreSQL storage trial

[CI run 36705862952](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36705862952)

Exact head: `01838710e86021e25663c16e1a5466e87a805e7f`. The complete workflow succeeded. All four PostgreSQL jobs and their merger succeeded. Downloaded evidence and parser output remain outside Git at `C:/Users/alexo/.codex/worktrees/kan71-schema-reset-checks/kan71-timing/ci-36705862952`. No local application tests or database processes were run to produce this analysis.

## Cost and test census

| Shard | Job seconds | Parallel step seconds | Serial step seconds | Parallel passed | Serial passed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 602 | 459 | 100 | 477 | 72 |
| 1 | 795 | 645 | 118 | 559 | 53 |
| 2 | 839 | 650 | 154 | 527 | 60 |
| 3 | 486 | 346 | 98 | 533 | 86 |

Four jobs: 2,722 seconds (45.3667 runner-minutes). Parallel steps: 2,100 seconds (35 minutes). Serial steps: 470 seconds (7.8333 minutes). Remaining job time: 152 seconds (2.5333 minutes). Merger: 26 seconds. **Total including merger: 2,748 seconds, 45.80 runner-minutes. The <=30-minute criterion is not met.**

The eight downloaded node-ID files contain 2,367 unique cases, with no duplicates: 2,096 parallel and 271 serial. No cases are missing from either retained reference census. Relative to the newer 2,360-case reference, the seven extras are the two rotation-isolation parameters, one SQLite report-job isolation regression, and four schema-reset parameters. Each lane's executed pass count equals its node-ID count. The merger's coverage artifact-presence check and combine succeeded. Its displayed aggregate PostgreSQL coverage is 75%; this lane is not the repository's global coverage gate.

The last successful automatic-worker comparison run (36696097087) took 53.75 runner-minutes for the four PostgreSQL jobs, excluding its merger. This trial's comparable 45.3667 minutes is 15.6% lower. The trial includes the intervening safe schema helper change and four additional selected tests; this is one run, not isolated proof of storage causality or a variance estimate. The failed 1 GiB run is excluded from timing comparisons.

## Observed storage headroom

All filesystems had 2,147,483,648 bytes capacity. Values below are MiB (2^20 bytes); each column is its own sampled maximum/minimum and may occur at a different timestamp.

| Shard/lane | Samples | Max df used MiB | Min df free MiB | Max base MiB | Max WAL MiB | Max inode used | Min inode free |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 parallel | 16 | 1232.520 | 815.480 | 224.477 | 1008 | 129143 | 1917538 |
| 0 serial | 4 | 1069.770 | 978.230 | 87.734 | 1008 | 3577 | 2043104 |
| 1 parallel | 21 | 1201.133 | 846.867 | 197.602 | 1008 | 143098 | 1903583 |
| 1 serial | 4 | 1063.066 | 984.934 | 84.184 | 992 | 4234 | 2042447 |
| 2 parallel | 22 | 1219.281 | 828.719 | 193.848 | 1024 | 136687 | 1909994 |
| 2 serial | 6 | 1082.820 | 965.180 | 83.234 | 1008 | 5101 | 2041580 |
| 3 parallel | 12 | 1247.590 | 800.410 | 240.578 | 1008 | 133850 | 1912831 |
| 3 serial | 4 | 1053.770 | 994.230 | 93.441 | 992 | 5672 | 2041009 |

Across 89 samples, the highest observed allocation was 1,308,192,768 bytes (61% in df output), leaving 839,290,880 bytes (800.410 MiB, 39.08%) at that sample. Maximum observed WAL allocation was 1 GiB. There were no recorded unavailable/racing-sample notices. Sampling is approximately every 30 seconds, df and du calls are not atomic, and these observed maxima do not prove continuous peak usage or guarantee future-suite headroom. The repaired allocation completed this run with substantial sampled byte and inode headroom.

## Observed PostgreSQL settings

All four jobs printed the same actual settings and passed the transaction-durability assertion:

- fsync, synchronous_commit and full_page_writes: on.
- max_wal_size: 1024 MB; min_wal_size: 80 MB.
- checkpoint_timeout: 300 seconds; checkpoint_completion_target: 0.9.
- wal_level: replica; wal_segment_size: 16,777,216 bytes.
- shared_buffers: 16,384 units of 8 KiB, or 128 MiB.

The pinned PostgreSQL/PostGIS image, worker count, test selection, real transaction behaviour, serial lane URLs and coverage gates were retained. tmpfs changes ephemeral test storage only; it does not establish host-power-loss durability. Root owns final repository documentation.
