"""Offline simulation only. No electrical control or energy generation."""
from dataclasses import dataclass
from itertools import combinations
from math import isfinite

@dataclass(frozen=True)
class Budget:
    grid_wh: float
    solar_wh: float
    battery_wh: float
    reserve_wh: float
    efficiency: float
    peak_w: float

    def available_wh(self):
        nums = (self.grid_wh,self.solar_wh,self.battery_wh,self.reserve_wh,self.efficiency,self.peak_w)
        if not all(isfinite(x) and x >= 0 for x in nums) or self.reserve_wh > self.battery_wh or not (0 < self.efficiency <= 1) or self.peak_w <= 0:
            raise ValueError("Invalid simulated budget")
        total = self.grid_wh + self.solar_wh + (self.battery_wh-self.reserve_wh)*self.efficiency
        if not isfinite(total): raise ValueError("Budget overflow")
        return total

@dataclass(frozen=True)
class Job:
    id: str
    power_w: float
    duration_h: float
    value: float

def plan(budget, jobs):
    """Optimize value of up to 16 independent serial jobs, with input-only capacity."""
    cap = budget.available_wh()
    if len(jobs)>16 or len(set(j.id for j in jobs)) != len(jobs): raise ValueError("Bad jobs")
    for j in jobs:
        if not j.id or not all(isfinite(x) and x >= 0 for x in (j.power_w,j.duration_h,j.value)) or j.power_w<=0 or j.duration_h<=0 or not isfinite(j.power_w*j.duration_h):
            raise ValueError("Invalid job")
    eligible=[j for j in jobs if j.power_w<=budget.peak_w]
    best=(0.0,0.0,())
    for count in range(len(eligible)+1):
        for subset in combinations(eligible,count):
            wh=sum(j.power_w*j.duration_h for j in subset)
            value=sum(j.value for j in subset)
            ids=tuple(sorted(j.id for j in subset))
            if wh<=cap and (value>best[0] or (value==best[0] and wh<best[1])):
                best=(value,wh,ids)
    return {"state":"SIMULATION_ONLY","provenance":"UNVERIFIED_INPUT","available_wh":cap,"scheduled_wh":best[1],"selected_jobs":list(best[2])}
