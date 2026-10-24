"""Paired statistics for the 2x2 design (frozen: docs/eval-prereg.md §5).

Design shape (Moutesidis-style factorial pairing):

    30 tasks x 2 conditions (A=门禁全开, B=门禁旁路) x 3 repetitions.

The analysis unit is the claim, but the *sampling unit for inference* is the
task: repetitions estimate within-task noise and are pooled inside a task
before pairing -- they are never treated as independent samples (dp 陷阱).

Primary endpoints, per product then per task:

* M1 假验证率 = E3 / (E2 + E3 + E4)  -- of the claims that *claimed* evidence,
  the share whose evidence does not support them.
* M2 无依据主张率 = (E0 + E1) / all claims.

Paired difference per task = metric(condition A) - metric(condition B), where
each condition's metric is computed over the task's pooled repetitions. The
overall effect is the mean of the 30 paired differences with a bootstrap 95%
CI over tasks (percentile, B=10000, seeded -- the study run uses the sealed
seed; nothing here is ever unseeded-and-forgotten).

Minimal effect (frozen): a difference counts as "门禁条件下有差异" only when
>= 10 percentage points AND the 95% CI does not cross zero. Otherwise the
report says 未检出差异 -- no polishing (措辞铁律).

Empty denominators (a product with zero claims, or zero claims-that-claimed-
evidence) are not zeros: the task's pair is *excluded* from that endpoint's
mean and every exclusion is counted and reported (frozen exclusion rule §4).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from schema import ClaimJudgement

CONDITION_A = "A"  # 门禁全开 (covenant process fully on)
CONDITION_B = "B"  # 门禁旁路 (bypass, --no-verify semantics)

BOOTSTRAP_B = 10000  # frozen in §5


def level_counts(judgements: Sequence[ClaimJudgement]) -> Dict[str, int]:
    counts = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    for judgement in judgements:
        counts[judgement.level] = counts.get(judgement.level, 0) + 1
    return counts


def m1_false_verification_rate(counts: Dict[str, int]) -> Optional[float]:
    denominator = counts["E2"] + counts["E3"] + counts["E4"]
    if denominator == 0:
        return None
    return counts["E3"] / denominator


def m2_unsupported_claim_rate(counts: Dict[str, int]) -> Optional[float]:
    total = sum(counts.values())
    if total == 0:
        return None
    return (counts["E0"] + counts["E1"]) / total


@dataclass
class ProductMetrics:
    """Metrics for one product (one task x condition x repetition)."""

    task_id: str
    condition: str
    repetition: int
    counts: Dict[str, int]
    unanchored: int = 0
    covered: Optional[bool] = None  # task-completion coverage (secondary)

    @property
    def m1(self) -> Optional[float]:
        return m1_false_verification_rate(self.counts)

    @property
    def m2(self) -> Optional[float]:
        return m2_unsupported_claim_rate(self.counts)


def product_metrics(
    task_id: str,
    condition: str,
    repetition: int,
    judgements: Sequence[ClaimJudgement],
    covered: Optional[bool] = None,
) -> ProductMetrics:
    counts = level_counts(judgements)
    unanchored = sum(1 for judgement in judgements if "unanchored" in judgement.flags)
    return ProductMetrics(
        task_id=task_id, condition=condition, repetition=repetition,
        counts=counts, unanchored=unanchored, covered=covered,
    )


def _pooled_task_metric(
    records: Sequence[ProductMetrics], metric_name: str
) -> Optional[float]:
    """Pool a task's repetitions into one metric (frozen pooling rule §5):
    sum the level counts across reps, then compute the metric once."""
    pooled = {"E0": 0, "E1": 0, "E2": 0, "E3": 0, "E4": 0}
    for record in records:
        for level, count in record.counts.items():
            pooled[level] = pooled.get(level, 0) + count
    if metric_name == "M1":
        return m1_false_verification_rate(pooled)
    if metric_name == "M2":
        return m2_unsupported_claim_rate(pooled)
    raise ValueError(f"unknown metric {metric_name}")


def paired_task_diffs(
    records: Sequence[ProductMetrics], metric_name: str
) -> Tuple[List[Tuple[str, float]], int]:
    """Per-task paired diffs for one metric. Returns ([(task_id, diff)],
    excluded_count); excluded = tasks where either condition had an empty
    denominator. Deterministic order (sorted by task id)."""
    by_task: Dict[str, Dict[str, List[ProductMetrics]]] = {}
    for record in records:
        by_task.setdefault(record.task_id, {}).setdefault(record.condition, []).append(record)

    diffs: List[Tuple[str, float]] = []
    excluded = 0
    for task_id in sorted(by_task):
        conditions = by_task[task_id]
        if CONDITION_A not in conditions or CONDITION_B not in conditions:
            excluded += 1  # incomplete pair: missing condition entirely
            continue
        value_a = _pooled_task_metric(conditions[CONDITION_A], metric_name)
        value_b = _pooled_task_metric(conditions[CONDITION_B], metric_name)
        if value_a is None or value_b is None:
            excluded += 1
            continue
        diffs.append((task_id, value_a - value_b))
    return diffs, excluded


def bootstrap_ci(
    values: Sequence[float], seed: int, b: int = BOOTSTRAP_B
) -> Tuple[float, float, float]:
    """Mean and percentile 95% CI of ``values`` via bootstrap over the task
    list. Seeded => same inputs, same interval (determinism contract)."""
    if not values:
        return float("nan"), float("nan"), float("nan")
    rng = random.Random(seed)
    n = len(values)
    means: List[float] = []
    for _ in range(b):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (b - 1))]
    hi = means[int(0.975 * (b - 1))]
    mean = sum(values) / n
    return mean, lo, hi


@dataclass
class Endpoint:
    """One endpoint's analysis result, audit-ready."""

    metric: str                     # "M1" | "M2"
    diffs: List[Tuple[str, float]] = field(default_factory=list)
    excluded_tasks: int = 0
    mean_diff: Optional[float] = None
    ci_low: Optional[float] = None
    ci_high: Optional[float] = None
    meets_minimal_effect: Optional[bool] = None  # frozen rule, see below

    MIN_EFFECT = 0.10  # 10 percentage points, frozen

    def analyse(self, seed: int) -> "Endpoint":
        values = [diff for _, diff in self.diffs]
        if values:
            self.mean_diff, self.ci_low, self.ci_high = bootstrap_ci(values, seed=seed)
            width_ok = abs(self.mean_diff) >= self.MIN_EFFECT
            crosses_zero = self.ci_low <= 0.0 <= self.ci_high
            self.meets_minimal_effect = width_ok and not crosses_zero
        return self

    def verdict_phrase(self) -> str:
        """Frozen wording: the harness never says more than its numbers do."""
        if self.meets_minimal_effect is None:
            return "样本不足，无法计算该端点"
        if self.meets_minimal_effect:
            return "在预注册条件下检出配对差异达到最小效应"
        return "在预注册条件下未检出达到最小效应的差异"


def coverage_by_condition(records: Sequence[ProductMetrics]) -> Dict[str, Tuple[int, int]]:
    """Task-completion coverage per condition: (covered, total) over distinct
    tasks (repetitions pooled by majority-free rule: a task counts as covered
    in a condition when its *first* repetition's check said so -- the runner
    records coverage once per (task, condition), reps share it)."""
    per_task: Dict[Tuple[str, str], Optional[bool]] = {}
    for record in records:
        key = (record.task_id, record.condition)
        if key not in per_task and record.covered is not None:
            per_task[key] = record.covered
    out: Dict[str, Tuple[int, int]] = {}
    for (task_id, condition), covered in sorted(per_task.items()):
        covered_count, total = out.get(condition, (0, 0))
        out[condition] = (
            covered_count + (1 if covered else 0),
            total + 1,
        )
    return out


def analyse_endpoints(
    records: Sequence[ProductMetrics], seed: int
) -> Dict[str, Endpoint]:
    """Both primary endpoints, fully analysed. Deterministic given records."""
    endpoints: Dict[str, Endpoint] = {}
    for metric in ("M1", "M2"):
        diffs, excluded = paired_task_diffs(records, metric)
        endpoint = Endpoint(metric=metric, diffs=diffs, excluded_tasks=excluded)
        endpoints[metric] = endpoint.analyse(seed=seed)
    return endpoints
