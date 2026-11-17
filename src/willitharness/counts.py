from dataclasses import dataclass


@dataclass(frozen=True)
class Counts:
    successes: int
    runs: int

    def __post_init__(self) -> None:
        assert self.runs >= 0, f"runs must not be negative, got {self.runs}"
        assert 0 <= self.successes <= self.runs, (
            f"successes must be between 0 and runs, got {self.successes} of {self.runs}"
        )

    def rate(self) -> float:
        assert self.runs >= 1, f"a rate needs at least one run, got {self.runs}"
        result = self.successes / self.runs
        assert 0.0 <= result <= 1.0, f"rate left [0, 1]: {result} from {self.successes} of {self.runs}"
        return result
