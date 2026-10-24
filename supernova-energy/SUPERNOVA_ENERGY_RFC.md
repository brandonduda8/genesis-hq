# Genesis Quantum Supernova Energy RFC — QSC-1
**Research proposal — no energy hardware deployed**

## Realistic architecture
Power source = utility grid and optional future professionally installed certified solar/storage/UPS. The Mini PC's energy demand must be measured before optimization. A quantum battery is not a usable power source today. The first product is a **read-only energy-aware compute scheduler**, not an electrical controller.

## Milestones
1. Zane verifies the mini PC's CPU, memory, idle and peak wall-plug watts and thermal behavior without credentials or changes.
2. Cody evaluates simulated grid/solar/battery budgets with a battery reserve, energy efficiency and peak power ceiling. Current prototype is serial task scheduling, not physical control.
3. Benchmark actual useful compute tasks per watt-hour, compared with the same CPU scheduling baseline. Report p50/p95, measured power and uncertainty.
4. Investigate pvlib, PyPSA, NREL REopt, OpenEMS, Network UPS Tools and Scaphandre after source/license audits. No installation until separately approved.
5. Research QuTiP for quantum-battery simulations, and ASE/Quantum ESPRESSO for energy-material simulations, with scientific reproducibility and explicit feasibility checks.

## Boundaries
No free-energy, perpetual-motion, or fabricated quantum performance claims; no live mains wiring, custom lithium circuits, public battery controllers, default cloud bills, privileged host actions or model-key transfers. Use approved physical electrical systems and qualified professionals if any electrical construction is undertaken. One canonical Genesis Mission Ledger; StarNet/Cody should only propose work and return evidence.

## Official references
https://qutip.org/
https://pvlib-python.readthedocs.io/
https://docs.pypsa.org/
https://docs.openems.io/
https://www.home-assistant.io/docs/energy/
https://github.com/networkupstools/nut
https://github.com/hubblo-org/scaphandre
https://www.quantum-espresso.org/
