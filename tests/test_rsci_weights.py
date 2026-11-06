import numpy as np

from lithology_thermal_rsci.rsci import RSCISettings


def test_weights_sum_to_one():
    assert np.isclose(sum(RSCISettings().resolved_weights().values()), 1.0)
