# RFC — Genesis Super CPU (software/hardware research)
**Status:** Research proposal. No physical GPU/QPU/CPU upgrade is claimed.

## Objective
Improve **measured end-to-end useful throughput** on the Ace Magic mini PC plus authorized compute nodes. Separate near-term software acceleration from long-term processor R&D.

## Phase A: Real CPU optimization, highest payoff
Audit exact SKU, OS, memory, SSD thermals, instruction set, power and cooling. Profile Python/Node/native workloads; remove needless background services, use bounded concurrency, SIMD/vectorization if supported, BLAS/OpenMP carefully, cache/IO control, quantization and memory mapping. Compare p50/p95 runtime, power, swap, RSS and correctness before calling it an improvement.

## Phase B: Distributed compute
Ray/Dask or existing Genesis router for task-level, independent CPU/GPU work. A remote GPU only counts if accessible, physically present and allocated under valid provider terms. Add data locality and job leases; no device resource inventing. Quantum algorithms do not turn a CPU into a GPU.

## Phase C: Open processor design
1. Define workload-specific target: memory bandwidth, low-power inference, SIMD/DSP, cryptographic acceleration or scheduling.
2. Evaluate RISC-V cores and extensions under actual open-source licenses. Simulate with gem5 and/or RTL using Verilator; unit/regression via cocotb.
3. RTL modules with Yosys synthesis; formal equivalence when possible; OpenROAD/LibreLane timing/area estimates with authorized open PDK, clearly marking estimated PPA.
4. No claims of manufacturability without DRC/LVS, signoff, packaging and actual fabrication funding.
5. Experiment with an FPGA only if hardware already exists and a separate owner-approved plan permits it.

## Quantum and quantum-inspired research
Use 2–12 simulated qubits first within bounded RAM. Compare OpenJij/OR-Tools against greedy baseline for real scheduling with matching constraints. Record failures too. A circuit benchmark is not evidence of quantum advantage.
