"""stats.py -- agreement, rates, effect sizes and exact tests (spec 9). Standard library only.

Every function is checked in the tests against a published worked value (see test_flinch.py, ST*).
Small samples get exact or permutation methods, and every report carries its n: an interval, never a lone
p-value. Where a quantity is undefined (no items, both coders using one category) it is returned as None
with the reason, never as 0 or 1.
"""
from __future__ import annotations

import itertools
import math
import random

Z95 = 1.959963984540054


def raw_agreement(a, b):
    if len(a) != len(b) or not a:
        return None
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)


def cohen_kappa(a, b):
    """(kappa, why). Two coders, the same items in the same order. None when chance agreement is 1."""
    if len(a) != len(b) or not a:
        return None, "no paired items"
    n, cats = len(a), sorted(set(a) | set(b))
    po = raw_agreement(a, b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    if pe >= 1.0:
        return None, "undefined: both coders used a single category throughout"
    return (po - pe) / (1.0 - pe), ""


def fleiss_kappa(table):
    """(kappa, why). table: one row per item, one count per category; every row sums to the same n raters."""
    if not table:
        return None, "no items"
    n = sum(table[0])
    if n < 2 or any(sum(r) != n for r in table):
        return None, "every item needs the same number (>= 2) of ratings"
    N, k = len(table), len(table[0])
    p = [sum(r[j] for r in table) / (N * n) for j in range(k)]
    P = [(sum(x * x for x in r) - n) / (n * (n - 1)) for r in table]
    pbar, pe = sum(P) / N, sum(x * x for x in p)
    if pe >= 1.0:
        return None, "undefined: every rating fell in one category"
    return (pbar - pe) / (1.0 - pe), ""


def wilson(k, n, z=Z95):
    if n == 0:
        return None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


def _binom_cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p), each term in log space (review finding 10: the direct product
    overflowed a float near n = 1,000)."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lp, lq, lnf = math.log(p), math.log1p(-p), math.lgamma(n + 1)
    return min(1.0, sum(math.exp(lnf - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
                        for i in range(k + 1)))


def _bisect(f, lo=0.0, hi=1.0, it=200):
    for _ in range(it):
        mid = (lo + hi) / 2
        if f(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson(k, n, alpha=0.05):
    """The exact binomial interval: lower solves P(X >= k) = alpha/2, upper solves P(X <= k) = alpha/2."""
    if n == 0:
        return None
    lower = 0.0 if k == 0 else _bisect(lambda p: 1 - _binom_cdf(k - 1, n, p) >= alpha / 2)
    upper = 1.0 if k == n else _bisect(lambda p: _binom_cdf(k, n, p) <= alpha / 2)
    return lower, upper


def newcombe_diff(k1, n1, k2, n2, z=Z95):
    """Difference of two proportions p1 - p2 with Newcombe's hybrid score interval (method 10)."""
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    (l1, u1), (l2, u2) = wilson(k1, n1, z), wilson(k2, n2, z)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def fisher_exact(a, b, c, d):
    """Two-sided p for the 2x2 table [[a, b], [c, d]]: the sum of tables at most as likely as the observed one."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    if n == 0:
        return None

    def prob(x):
        return math.comb(r1, x) * math.comb(r2, c1 - x) / math.comb(n, c1)
    obs = prob(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= obs * (1 + 1e-9)))


def permutation_test(x, y, n_perm=10000, seed=0, exact_limit=20000):
    """Two-sided test of mean(x) - mean(y). Exact enumeration when the arrangements number at most
    exact_limit; otherwise Monte Carlo with a fixed seed, p = (hits + 1) / (n_perm + 1). Returns (diff, p, method)."""
    if not x or not y:
        return None, None, "empty group"
    pool, nx = list(x) + list(y), len(x)
    obs = sum(x) / nx - sum(y) / len(y)
    total = math.comb(len(pool), nx)
    if total <= exact_limit:
        hits = 0
        tot = sum(pool)
        for idx in itertools.combinations(range(len(pool)), nx):
            sx = sum(pool[i] for i in idx)
            if abs(sx / nx - (tot - sx) / len(y)) >= abs(obs) - 1e-12:
                hits += 1
        return obs, hits / total, "exact (%d arrangements)" % total
    rng, hits = random.Random(seed), 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        if abs(sum(pool[:nx]) / nx - sum(pool[nx:]) / len(y)) >= abs(obs) - 1e-12:
            hits += 1
    return obs, (hits + 1) / (n_perm + 1), "Monte Carlo (%d permutations, seed %d)" % (n_perm, seed)


def rate_line(name, k, n):
    """One reported rate: k of n, the proportion, Wilson and exact intervals. n = 0 reads UNDETERMINED."""
    if n == 0:
        return {"name": name, "k": 0, "n": 0, "rate": None, "note": "UNDETERMINED: no eligible items"}
    return {"name": name, "k": k, "n": n, "rate": k / n, "wilson95": wilson(k, n), "exact95": clopper_pearson(k, n),
            "note": "small sample: read the exact interval" if n < 30 else ""}


def compare_to_control(target, control):
    """Target rate against a matched control rate: difference with Newcombe's interval and Fisher's exact p."""
    (k1, n1), (k2, n2) = target, control
    if n1 == 0 or n2 == 0:
        return {"difference": None, "note": "UNDETERMINED: a group has no items"}
    d, lo, hi = newcombe_diff(k1, n1, k2, n2)
    return {"difference": d, "newcombe95": (lo, hi), "fisher_p": fisher_exact(k1, n1 - k1, k2, n2 - k2),
            "note": "the interval includes 0: not distinguishable from the control at this n" if lo <= 0 <= hi else ""}
