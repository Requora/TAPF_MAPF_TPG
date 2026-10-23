# Trajectory performance benchmark

[中文](../../zh/development/0014-trajectory-performance.md) | [English](../../en/development/0014-trajectory-performance.md)

<!-- doc-sync: trajectory-performance / 2026-10-23-r1 -->

## Findings and scope

Repeated full-knot validation in the public API is the main hotspot. At 1000 robots, 128 knots per curve and 50 Hz queries, median fleet evaluation takes 80.406 ms, exceeding the 20 ms period. This does not establish that Python itself is unsuitable; next evaluate validating once and indexing intervals. This PR adds measurements without changing production code.

## Method and reproduction

Synthetic inputs, not native trajectories or real execution. Each robot stores a separate constant-speed straight curve, x=t and y=robot index, with 1 s knot spacing. Queries start mid-curve and advance by 1/hz. Evaluation and slicing are timed separately; slice length is 1/hz. One thread processes the whole fleet serially; no pacing or real scheduler is simulated, and Hz only sets query spacing and comparison budget. Each case warms up for 3 frames, then measures 5 repeats of 3 frames, totaling 15 samples. Timing includes public API validation, interpolation and output allocation; setup and analytic result checks are excluded, as are solvers, continuous geometry, IPC and backends. GC remains enabled; no single CPU is pinned. Fixed case order and hot repeats may bias caches/frequency; shared-host load was not isolated, and tests also ran during later measurements. p95 describes only these 15 frames, not a real-time guarantee.

- UTC: `2026-10-23T06:22:13.620449+00:00`.
- CPU: AMD Ryzen Threadripper 3990X 64-Core Processor. Python: `3.14.7`.
- OS: `Linux-7.0.0-34-generic-x86_64-with-glibc2.39`. CPU affinity: `0-127`.
- Measurement baseline: `e6372cc251e3314b40beec18ca50097581339a60`.
- benchmark.py SHA256: `c693aa655809261076d4ed3010c78f235d0de2d2c9524849bd955cd96b116275`.
- Raw JSON SHA256: `69ba9b63ee131182bb8fc7f69c58626ecedb9e9d5651a4fa207acc94f66414b5`.
- trajectory/__init__.py SHA256: `cb05e79155b35c4964c84312e0379c486ddd2d87fc97c93c53da90792936c9a2`.
- trajectory/_curve.py SHA256: `f4a0db59f2ed9e04443d0b0fc1ad66a866f575421bb993ff78c9de3b3b85f059`.
- trajectory/_validation.py SHA256: `15f276f3a9473fdc33935fec2b26700a213824bbcd336a575d2e17ebb6a7766f`.

```bash
PYTHONPATH=src:tests python -m trajectory.benchmark --output /tmp/trajectory-benchmark.json > /tmp/trajectory-benchmark.log
PYTHONPATH=src:tests python -m cProfile -s cumulative -m trajectory.benchmark --robots 100 --knots 1024 --hz 50 --frames 3 --repeats 1 --output /tmp/trajectory-profile.json
PYTHONPATH=src python -m unittest discover -s tests -p test_benchmark.py -v
```

TDD: the workload test first failed because the benchmark module was absent, then passed. It checks separate fleet data, API call counts and analytic positions without speed thresholds. Source and the previously clean-installed wheel both run 104 tests: 103 pass, one CBS-TA skip; production source is unchanged, so the wheel was not rebuilt.

## Measured comparison

Times are ms per whole-fleet frame. The 10 Hz budget is 100 ms; 50 Hz is 20 ms. Operations are measured separately, not combined into a claimed full-pipeline time.

| Robots | Knots/robot | Hz | Operation | Median ms | p95 ms | Median/period |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 16 | 10 | evaluate | 0.018 | 0.020 | 0.00 |
| 1 | 16 | 10 | slice_curve | 0.026 | 0.037 | 0.00 |
| 1 | 16 | 50 | evaluate | 0.016 | 0.017 | 0.00 |
| 1 | 16 | 50 | slice_curve | 0.022 | 0.024 | 0.00 |
| 1 | 128 | 10 | evaluate | 0.081 | 0.087 | 0.00 |
| 1 | 128 | 10 | slice_curve | 0.094 | 0.102 | 0.00 |
| 1 | 128 | 50 | evaluate | 0.082 | 0.094 | 0.00 |
| 1 | 128 | 50 | slice_curve | 0.094 | 0.101 | 0.00 |
| 1 | 1024 | 10 | evaluate | 0.643 | 0.658 | 0.01 |
| 1 | 1024 | 10 | slice_curve | 0.697 | 0.705 | 0.01 |
| 1 | 1024 | 50 | evaluate | 0.639 | 0.652 | 0.03 |
| 1 | 1024 | 50 | slice_curve | 0.693 | 0.720 | 0.03 |
| 100 | 16 | 10 | evaluate | 1.498 | 1.532 | 0.01 |
| 100 | 16 | 10 | slice_curve | 2.190 | 2.212 | 0.02 |
| 100 | 16 | 50 | evaluate | 1.509 | 1.534 | 0.08 |
| 100 | 16 | 50 | slice_curve | 2.187 | 2.202 | 0.11 |
| 100 | 128 | 10 | evaluate | 8.159 | 8.235 | 0.08 |
| 100 | 128 | 10 | slice_curve | 9.375 | 9.433 | 0.09 |
| 100 | 128 | 50 | evaluate | 8.234 | 8.287 | 0.41 |
| 100 | 128 | 50 | slice_curve | 9.356 | 9.439 | 0.47 |
| 100 | 1024 | 10 | evaluate | 64.665 | 73.538 | 0.65 |
| 100 | 1024 | 10 | slice_curve | 69.365 | 70.084 | 0.69 |
| 100 | 1024 | 50 | evaluate | 63.599 | 64.529 | 3.18 |
| 100 | 1024 | 50 | slice_curve | 67.923 | 68.467 | 3.40 |
| 1000 | 16 | 10 | evaluate | 14.595 | 14.721 | 0.15 |
| 1000 | 16 | 10 | slice_curve | 21.413 | 27.538 | 0.21 |
| 1000 | 16 | 50 | evaluate | 14.515 | 14.728 | 0.73 |
| 1000 | 16 | 50 | slice_curve | 21.439 | 21.951 | 1.07 |
| 1000 | 128 | 10 | evaluate | 80.514 | 81.331 | 0.81 |
| 1000 | 128 | 10 | slice_curve | 92.863 | 93.718 | 0.93 |
| 1000 | 128 | 50 | evaluate | 80.406 | 81.122 | 4.02 |
| 1000 | 128 | 50 | slice_curve | 93.853 | 178.649 | 4.69 |
| 1000 | 1024 | 10 | evaluate | 615.706 | 662.295 | 6.16 |
| 1000 | 1024 | 10 | slice_curve | 678.060 | 1211.334 | 6.78 |
| 1000 | 1024 | 50 | evaluate | 612.875 | 619.971 | 30.64 |
| 1000 | 1024 | 50 | slice_curve | 661.102 | 687.491 | 33.06 |

## Hotspots and limits

Separate cProfile run: 100 robots, 1024 knots, 50 Hz. Combined cumulative time in the two public APIs is 3.778 s; check_knots accounts for 3.715 s, about 98%, including full input checks and output-knot checks. Profiling significantly adds overhead, so these times are excluded from the table above. This supports first reducing repeated validation; no speedup is implemented or claimed. Linear interval scanning also remains to be addressed as curves grow.

## Raw frame times

All measured samples below match frame_ms in the JSON, in ms. Every case has analytic position error below 1e-9 m and x-velocity error below 1e-9 m/s; this is not collision validation.

<details>
<summary>Expand 36 raw sample groups</summary>

| robots / knots / Hz / API | frame_ms |
| --- | --- |
| 1 / 16 / 10 / evaluate | 0.019507, 0.018635, 0.018555, 0.018105, 0.017854, 0.018105, 0.018195, 0.017764, 0.017994, 0.017834, 0.017994, 0.017753, 0.017914, 0.017583, 0.017733 |
| 1 / 16 / 10 / slice_curve | 0.026661, 0.029807, 0.026580, 0.026320, 0.036559, 0.026350, 0.026019, 0.026160, 0.026531, 0.026099, 0.026009, 0.026190, 0.025749, 0.025899, 0.026831 |
| 1 / 16 / 50 / evaluate | 0.016932, 0.016231, 0.016211, 0.016020, 0.015990, 0.016020, 0.015940, 0.015790, 0.015810, 0.015639, 0.015920, 0.015529, 0.015920, 0.015759, 0.015550 |
| 1 / 16 / 50 / slice_curve | 0.024046, 0.023334, 0.023504, 0.023104, 0.022853, 0.022913, 0.022603, 0.022483, 0.022463, 0.022142, 0.022202, 0.022112, 0.022232, 0.022062, 0.022162 |
| 1 / 128 / 10 / evaluate | 0.081274, 0.082197, 0.080613, 0.081144, 0.083138, 0.081225, 0.080363, 0.080522, 0.080613, 0.080733, 0.087186, 0.080834, 0.080973, 0.081074, 0.080934 |
| 1 / 128 / 10 / slice_curve | 0.093988, 0.101803, 0.093628, 0.093388, 0.093437, 0.093397, 0.092696, 0.102185, 0.095291, 0.094249, 0.092726, 0.094188, 0.101102, 0.095631, 0.092385 |
| 1 / 128 / 50 / evaluate | 0.081745, 0.094420, 0.089780, 0.081334, 0.081875, 0.081224, 0.083168, 0.081935, 0.082156, 0.081986, 0.080964, 0.081064, 0.081365, 0.082457, 0.090893 |
| 1 / 128 / 50 / slice_curve | 0.094489, 0.093818, 0.093127, 0.093728, 0.101252, 0.094109, 0.093517, 0.092766, 0.093167, 0.094790, 0.093317, 0.094489, 0.096282, 0.093247, 0.100842 |
| 1 / 1024 / 10 / evaluate | 0.636349, 0.637671, 0.644423, 0.658370, 0.646659, 0.643152, 0.644885, 0.630508, 0.634835, 0.640907, 0.634996, 0.644524, 0.636238, 0.642861, 0.644875 |
| 1 / 1024 / 10 / slice_curve | 0.699608, 0.699428, 0.691333, 0.701973, 0.687636, 0.686153, 0.682316, 0.696313, 0.685783, 0.698366, 0.697314, 0.697725, 0.692195, 0.705399, 0.701983 |
| 1 / 1024 / 50 / evaluate | 0.630508, 0.634174, 0.641257, 0.640666, 0.636358, 0.639194, 0.632462, 0.638342, 0.638422, 0.642720, 0.640406, 0.652268, 0.636358, 0.651017, 0.650485 |
| 1 / 1024 / 50 / slice_curve | 0.698937, 0.678147, 0.693578, 0.693276, 0.685432, 0.694128, 0.707193, 0.674832, 0.699920, 0.693096, 0.677036, 0.683738, 0.680131, 0.719987, 0.691874 |
| 100 / 16 / 10 / evaluate | 1.496913, 1.498496, 1.485822, 1.532390, 1.496372, 1.500429, 1.505760, 1.496883, 1.492645, 1.491813, 1.494779, 1.501832, 1.510289, 1.512382, 1.498707 |
| 100 / 16 / 10 / slice_curve | 2.182154, 2.189969, 2.211610, 2.184208, 2.184549, 2.177155, 2.195871, 2.185811, 2.203475, 2.189348, 2.187024, 2.194688, 2.194518, 2.199707, 2.195339 |
| 100 / 16 / 50 / evaluate | 1.532781, 1.505359, 1.508695, 1.501371, 1.533633, 1.511711, 1.517732, 1.514676, 1.504086, 1.508185, 1.504768, 1.520007, 1.503215, 1.525096, 1.496081 |
| 100 / 16 / 50 / slice_curve | 2.202032, 2.188716, 2.194237, 2.176123, 2.180541, 2.182135, 2.198405, 2.188727, 2.177485, 2.189418, 2.186783, 2.176814, 2.165412, 2.188135, 2.182906 |
| 100 / 128 / 10 / evaluate | 8.141442, 8.120582, 8.073664, 7.992349, 8.036522, 8.235350, 8.161069, 8.175256, 8.126413, 8.142635, 8.159467, 8.227696, 8.192308, 8.212276, 8.159887 |
| 100 / 128 / 10 / slice_curve | 9.390083, 9.384773, 9.383622, 9.366279, 9.375355, 9.432974, 9.322896, 9.381276, 9.395173, 9.344176, 9.393871, 9.358574, 9.359024, 9.326733, 9.334337 |
| 100 / 128 / 50 / evaluate | 8.287009, 8.257352, 8.250219, 8.220652, 8.213238, 8.233687, 8.254897, 8.254737, 8.229339, 8.176890, 8.176979, 8.284083, 8.259506, 8.187109, 8.185275 |
| 100 / 128 / 50 / slice_curve | 9.313227, 9.330059, 9.356450, 9.438506, 9.401636, 9.305383, 9.340770, 9.373772, 9.373452, 9.339918, 9.366639, 9.380986, 9.308117, 9.356360, 9.358343 |
| 100 / 1024 / 10 / evaluate | 65.163867, 73.538422, 66.431876, 63.974578, 64.142688, 64.166904, 64.409404, 64.553047, 64.763627, 64.808553, 64.929051, 64.995527, 64.665370, 64.435084, 63.872134 |
| 100 / 1024 / 10 / slice_curve | 70.083831, 69.863002, 69.392668, 68.854787, 69.977600, 69.329338, 69.616724, 69.835088, 69.181227, 69.364535, 69.581126, 68.341182, 69.011625, 68.947232, 69.096005 |
| 100 / 1024 / 50 / evaluate | 63.650032, 63.116489, 63.270942, 63.280911, 63.462967, 64.036656, 63.473627, 63.234583, 63.729252, 64.529022, 63.598595, 63.677895, 63.785640, 63.497242, 63.701630 |
| 100 / 1024 / 50 / slice_curve | 68.440781, 68.466630, 68.304162, 68.031633, 67.880126, 68.264786, 67.922747, 68.020804, 67.676660, 67.974434, 67.832145, 67.729439, 67.709412, 67.886969, 67.551372 |
| 1000 / 16 / 10 / evaluate | 14.511780, 14.558288, 14.590540, 14.595109, 14.612261, 14.564530, 14.632951, 14.656936, 14.619264, 14.617180, 14.586964, 14.720987, 14.558640, 14.569701, 14.670713 |
| 1000 / 16 / 10 / slice_curve | 21.351821, 21.408638, 21.441551, 21.902366, 21.399040, 21.377600, 21.505343, 21.884192, 27.538079, 21.365898, 21.380716, 21.329798, 21.677710, 21.450819, 21.412737 |
| 1000 / 16 / 50 / evaluate | 14.629755, 14.682024, 14.727700, 14.376193, 14.383747, 14.386983, 14.486342, 14.442839, 14.487545, 14.495780, 14.581623, 14.628983, 14.515427, 14.545724, 14.542068 |
| 1000 / 16 / 50 / slice_curve | 21.549036, 21.352052, 21.368903, 21.951109, 21.329779, 21.436211, 21.439057, 21.841571, 21.314189, 21.329568, 21.377770, 21.838585, 21.512756, 21.529408, 21.580786 |
| 1000 / 128 / 10 / evaluate | 81.331011, 80.371639, 80.677470, 80.650930, 80.083081, 80.348996, 80.258845, 80.117878, 80.516744, 80.927866, 80.841612, 80.513790, 80.092519, 80.295274, 80.630361 |
| 1000 / 128 / 10 / slice_curve | 92.694593, 92.862742, 93.210443, 93.591256, 92.463854, 92.649447, 92.713939, 93.138556, 93.149437, 92.723918, 92.338186, 93.717776, 93.202387, 93.012466, 92.603068 |
| 1000 / 128 / 50 / evaluate | 80.405824, 80.010975, 80.555188, 79.877731, 80.592569, 80.571158, 79.866761, 79.804994, 80.379253, 80.884804, 80.341632, 80.450418, 81.122465, 79.965568, 80.724780 |
| 1000 / 128 / 50 / slice_curve | 93.157491, 93.355097, 96.053582, 178.649124, 94.049846, 94.802025, 94.579222, 95.013396, 93.576077, 93.432995, 94.804760, 93.853394, 92.331973, 93.812406, 93.314430 |
| 1000 / 1024 / 10 / evaluate | 631.200205, 626.783216, 628.442127, 612.515730, 609.973141, 612.866996, 619.859256, 653.604013, 662.294608, 610.093369, 613.512221, 615.033060, 612.274020, 617.795046, 615.706018 |
| 1000 / 1024 / 10 / slice_curve | 681.675946, 674.707271, 676.334500, 680.525681, 680.669264, 682.735096, 678.446732, 678.059997, 678.388131, 677.741813, 1211.333952, 676.004413, 670.619166, 668.162860, 673.290018 |
| 1000 / 1024 / 50 / evaluate | 616.219201, 619.971277, 617.055419, 613.638079, 616.638988, 609.821129, 609.404339, 613.698403, 608.267388, 612.874699, 608.287727, 617.921423, 605.144378, 606.257902, 611.019915 |
| 1000 / 1024 / 50 / slice_curve | 660.272895, 671.456174, 687.490676, 659.271603, 660.862604, 667.165515, 659.300709, 661.101929, 658.321389, 660.375239, 675.002538, 667.685341, 659.615325, 668.585321, 663.702898 |

</details>
