# Genesis Quantum Forge — Research Layer
**Status: STAGED / NOT DEPLOYED.** This subsystem does not grant access to a QPU, GPU, or fabrication facility. It cannot make a classical CPU quantum.

## Three lanes
1. **Quantum circuit lab:** Qiskit, PennyLane/Lightning, Cirq, QuTiP, Qulacs, Stim + PyMatching, OpenFermion, CUDA-Q. Start with a small local Bell-state simulation and unit tests before selecting frameworks. Beware state-vector simulation uses O(2^n) memory; avoid large qubit counts on the mini PC.
2. **Quantum-inspired optimization:** OpenJij and OR-Tools CP-SAT; benchmark against greedy/local search on *identical* Genesis scheduling datasets, constraints, and time limits. Quantum-inspired does not imply quantum speedup.
3. **Super CPU architecture:** RISC-V ISA, gem5, Verilator+cocotb, Yosys, OpenROAD/LibreLane, open PDK where licensed. Start with a small simulated RISC-V extension or accelerator; formally/specifically test correctness, workloads, power, area and timing estimates. FPGA prototyping or silicon fabrication is a later separately approved investment.

## System integration proposal
Genesis Mission Ledger -> Cody research ticket -> verified isolated CPU simulator -> reproducible fixture/benchmark -> independent QA -> evidence receipt -> Phoenix read-only dashboard. Zane to report mini PC CPU/RAM/GPU/virtualization first. StarNet may provide a bounded, approved task UI but must not own the canonical ledger.

## Guardrails
No install, API key use, paid QPU/GPU, remote provider account, host deployment, firmware flash, unrestricted shell, network exposure, crypto replacement, claims of physical quantum advantage, or auto-merge by this draft. Preserve $0 added spend. Quantum circuits are experiments, not proof of improvement. Post-quantum cryptography future readiness should use NIST standardized algorithms through vetted libraries, not DIY crypto.

## Starting results
A dependency-free 2-qubit Bell simulator and tests are proposed in this PR. This toy program is not an optimized quantum computing engine; its purpose is to establish a reproducible baseline and an honest learning path.

## Primary official sources
- https://github.com/Qiskit/qiskit
- https://github.com/Qiskit/qiskit-aer
- https://github.com/PennyLaneAI/pennylane
- https://github.com/quantumlib/Cirq
- https://github.com/NVIDIA/cuda-quantum
- https://github.com/quantumlib/Stim
- https://github.com/oscarhiggott/PyMatching
- https://github.com/quantumlib/OpenFermion
- https://github.com/openjij/openjij
- https://github.com/google/or-tools
- https://www.gem5.org/
- https://github.com/ucb-bar/chipyard
- https://github.com/YosysHQ/yosys
- https://github.com/verilator/verilator
- https://github.com/cocotb/cocotb
- https://openroad.org/
- https://librelane.readthedocs.io/
- https://csrc.nist.gov/projects/post-quantum-cryptography
