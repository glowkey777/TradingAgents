# -*- coding: utf-8 -*-
"""Similarity：连续特征 z-score 距离（第一版接口，baseline 用精确匹配）。"""
from __future__ import annotations

import pandas as pd


def zscore_distance(current: dict[str, float], history: pd.DataFrame,
                    features: list[str]) -> pd.Series:
    """每个历史样本与当前状态的 z-score 距离（PIT-safe：历史只用当时及以前）。

    当前版本：计算当前值在历史 distribution 中的 z-score，距离 = |z|。
    返回 Series（index=历史日期，value=距离），NaN 表示该历史样本缺失该特征。
    """
    dist = pd.Series(0.0, index=history.index)
    for feat in features:
        if feat not in history.columns or current.get(feat) is None:
            continue
        hist = history[feat]
        mu, sd = hist.mean(), hist.std(ddof=0)
        if sd == 0 or pd.isna(sd):
            continue
        z = (current[feat] - mu) / sd
        # 距离用 |z|，但保留每历史样本的该特征 z 分量
        dz = (hist - mu) / sd
        dist = dist + (dz - z).abs()
    return dist
