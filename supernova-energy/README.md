# Genesis Quantum Supernova Core (QSC-1)

**Status:** experimental engineering prototype; local tests passed. Not deployed to Genesis, StarNet, Zane's runtime, the Ace Magic mini PC, or any energy hardware. No remote energy generation or quantum battery claimed.

## Mission
Build a real, upgradeable power-and-compute laboratory inside Genesis HQ. Use existing grid power, supported solar generation and certified energy storage for physical energy; optimize how useful compute jobs consume that energy. Research quantum energy storage and new energy materials scientifically and separately from operational power systems.

## Architecture

```
PHYSICAL ENERGY: grid / (future certified solar + inverter) / (optional certified UPS)
             -> safe power delivery -> mini PC + network + storage
             -> read-only measurements (wattmeter/UPS/RAPL where available)
                                        |
SOFTWARE: Genesis Mission Ledger -> Cody Supernova Energy Planner (proposal-only)
                                        |
            measured power, uptime, thermals, quotas, task priorities
                                        |
                              owner-approved job scheduler
                                        |
                 compute workers / model training / CI / lab simulation
                                        |
                          metrics, hashed receipts, independent QA

SEPARATE RESEARCH: quantum batteries / material simulation / solar cell research
                  never connected to electrical power controls
```

## Prototype
`energy_planner.py` implements a small offline, exact-enumeration selection model for at most 16 **serial** jobs. `test_energy_planner.py` contains 14 standard-library unit tests. It never reads or controls live equipment or uses secrets. Inputs are user-supplied and **UNVERIFIED**. Current model omits battery charging/discharging rate, timestamps, actual solar irradiance, standby loads, thermal time constants and simultaneous task execution. It must not be used to operate real equipment.

Run from this directory:

```bash
python3 -m unittest discover -v
python3 energy_planner.py
```

## Project laws
- No free energy, perpetual-motion claims, or misleading quantum advantage.
- No mains/wiring work by Cody. Electrical changes and solar/battery systems require appropriate certified components and qualified installers.
- Do not expose UPS or battery controls to StarNet or any general-purpose agent.
- $0 incremental spending unless owner authorizes a separate acquisition. Software simulation and publicly licensed research only.
- All production changes, power control, remote provider use and firmware changes separately authorized.
- One canonical Genesis Mission Ledger; StarNet and Cody report evidence but do not create a second authority.

## Related work
- Genesis Quantum Forge proposal: `brandonduda8/genesis-hq` PR #7.
- Genesis mini PC / Cody Alliance: `brandonduda8/astra-zane-bridge` issue #80.
- Cody training / StarNet: `brandonduda8/astra-zane-bridge` issue #82.
- Quantum Forge and Super CPU: `brandonduda8/astra-zane-bridge` issue #83.

See `SUPERNOVA_ENERGY_RFC.md` for the phased technical proposal and official sources.