# -*- coding: utf-8 -*-
"""P1 数据配置：dataset_version、symbol mapping、canonical price 决策。"""
from __future__ import annotations

# Canonical price 决策（用户拍板）
PRICE_BASIS = "unadjusted"          # canonical = 未复权价
ADJUSTMENT = "NONE"
AVAILABILITY_POLICY = "session_close_plus_buffer"   # 收盘后可用
TIMEZONE = "America/New_York"

# 期权链数据源（能力探测：OpenD；不支持历史链则 P8 接专门源）
OPTION_CHAIN_SOURCE = "opend"
OPTION_CHAIN_HISTORICAL = {
    "realtime_recent": "VERIFIED",            # 实测能拉当前链（350 行/天，含 strike/expiration/type）
    "historical_pit_reconstruct": "UNVERIFIED",  # 能否重建"历史时点当时的链"，P8 验证（非"现在查历史"）
}

# yfinance symbol mapping + 单位（不许凭记忆硬编码，实测后确认）
YFINANCE_SYMBOLS = {
    "spy_close": ("SPY", "usd"),
    "vix":       ("^VIX", "index"),
    "us5y":      ("^FVX", "percent"),   # 收益率，5.03 = 5.03%
    "us10y":     ("^TNX", "percent"),
    "dxy":       ("DX-Y.NYB", "index"),
    "wti":       ("CL=F", "usd"),
}

# dataset 版本（变化必须可追踪）
DATASET_VERSIONS = {
    "spy_daily": "spy_daily_v1",
    "spy_intraday": "opend_intraday_v1",
    "macro_daily": "macro_daily_yf_v1",
    "options": "opend_options_v1",
}

# Canonical 数据根目录
RAW_DIR = r"F:\Youtube\stock"
NORMALIZED_DIR = r"F:\Youtube\0413\TradingAgents\data\normalized"
REPOSITORY_DIR = r"F:\Youtube\0413\TradingAgents\data\canonical"
