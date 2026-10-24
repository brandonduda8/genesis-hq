"""Tiny educational 2-qubit statevector simulation; no dependencies or hardware/QPU claims."""
from math import sqrt
from typing import Tuple

State = Tuple[complex, complex, complex, complex]

def apply_h_first(state: State) -> State:
    """H on leftmost qubit, basis |00>,|01>,|10>,|11>."""
    return tuple((state[i] + state[i + 2]) / sqrt(2) if i < 2 else
                 (state[i - 2] - state[i]) / sqrt(2) for i in range(4))  # type: ignore[return-value]

def apply_cnot_first_control(state: State) -> State:
    return (state[0], state[1], state[3], state[2])

def bell_state() -> State:
    return apply_cnot_first_control(apply_h_first((1+0j, 0j, 0j, 0j)))

def probabilities(state: State):
    return tuple(abs(a)**2 for a in state)

if __name__ == "__main__":
    print(dict(zip(("00", "01", "10", "11"), probabilities(bell_state()))))
