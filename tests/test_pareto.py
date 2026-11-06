import pandas as pd

from lithology_thermal_rsci.pareto import mark_pareto_front


def test_pareto_front():
    table = pd.DataFrame([
        {"lithology": "sand", "candidate": "a", "R2_OOF": 0.8, "RSCI_0_100": 90},
        {"lithology": "sand", "candidate": "b", "R2_OOF": 0.9, "RSCI_0_100": 80},
        {"lithology": "sand", "candidate": "c", "R2_OOF": 0.7, "RSCI_0_100": 70},
    ])
    result = mark_pareto_front(table)
    flags = dict(zip(result["candidate"], result["pareto_optimal"]))
    assert flags == {"a": True, "b": True, "c": False}
