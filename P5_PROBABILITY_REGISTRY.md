# P5_PROBABILITY_REGISTRY.md — Probability Registry

| Name | Method | Inputs | Horizon | alpha | min_sample | low_sample | Version |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| baseline_unconditional | unconditional | none (unconditional historical target distribution) | T+1 | 1.0 | 30 | 100 | v1 |
| baseline_regime_conditional | regime_conditional | P4 regime (trend/volatility/macro/event argmax) | T+1 | 1.0 | 30 | 100 | v1 |
| baseline_event_conditional | event_conditional | P3 events (weighted) | T+1 | 1.0 | 30 | 100 | v1 |
| baseline_hierarchical | hierarchical | P4 regime + P3 events + P2 features | T+1 | 1.0 | 30 | 100 | v1 |

Smoothing = Laplace；Calibration = Identity（NOT_CALIBRATED）。