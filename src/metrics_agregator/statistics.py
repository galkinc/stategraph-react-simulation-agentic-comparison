from scipy.stats import wilcoxon
import numpy as np
from statsmodels.stats.contingency_tables import mcnemar

def wilcoxon_test(values_a, values_b):
    if len(values_a) == 0:
        return None, None
    if np.allclose(values_a, values_b):
        return 0.0, 1.0
    
    stat, p = wilcoxon(values_a, values_b)
    return stat, p

def mcnemar_success(pairs):

    table = np.zeros((2,2), dtype=int)

    for react, sg in pairs:
        if react.success is None or sg.success is None:
            continue
        table[int(react.success)][int(sg.success)] += 1

    result = mcnemar(table, exact=True)

    return result.statistic, result.pvalue

def bootstrap_delta(values_a, values_b, n=5000):
    if len(values_a) < 2:
        return None, None, None

    a = np.array(values_a)
    b = np.array(values_b)

    n_samples = len(a)
    deltas = []

    for _ in range(n):

        idx = np.random.randint(0, n_samples, n_samples)

        #delta = np.median(b[idx]) - np.median(a[idx])
        # a - react, b - sg
        # Delta = Treatment − Control = ReAct − StateGraph
        delta = np.median(a[idx]) - np.median(b[idx])
        deltas.append(delta)

    deltas = np.array(deltas)

    return (
        np.median(deltas),
        np.percentile(deltas, 2.5),
        np.percentile(deltas, 97.5),
    )