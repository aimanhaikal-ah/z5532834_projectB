"""Offline tests for portfolio construction helpers."""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src import portfolios  # noqa: E402


def test_risk_parity_weights_equalise_risk_contributions():
    returns = pd.DataFrame(
        {
            "LowVol": [0.001, 0.002, -0.001, 0.0015, -0.0005, 0.001],
            "MedVol": [0.003, -0.002, 0.004, -0.001, 0.002, -0.003],
            "HighVol": [0.010, -0.012, 0.014, -0.009, 0.011, -0.010],
        }
    )

    weights = portfolios._optimise_weights(
        returns,
        method="risk_parity",
        max_weight=1.0,
    )
    cov = returns.cov().to_numpy() + np.eye(returns.shape[1]) * 1e-8
    contributions = portfolios._risk_contributions(weights, cov)
    contribution_shares = contributions / contributions.sum()

    assert np.isclose(weights.sum(), 1.0)
    assert (weights >= 0).all()
    assert np.allclose(contribution_shares, np.repeat(1 / 3, 3), atol=0.03)
