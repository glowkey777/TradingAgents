# -*- coding: utf-8 -*-
"""Macro Symbol 元数据：记录每个宏观标的的 ticker/字段/单位/含义。

任务书 P1 第 15 节要求：不要假设 Yahoo ticker 就是生产定义，
必须记录实际返回的字段、单位和含义。
"""
from __future__ import annotations

from pydantic import BaseModel


class MacroSourceMeta(BaseModel):
    symbol: str                 # 内部统一 symbol
    yahoo_ticker: str           # 实际抓取用的 ticker
    field: str                  # 内部 field 名
    description: str            # 含义
    unit: str                   # 单位
    scale: float = 1.0          # 原始值 × scale = 内部值（如 10Y 收益率 5.03 = 5.03%）
    source: str = "yfinance"
    notes: str = ""


# 实际由 F:\Youtube\stock\spy_macro_2013_2026.csv（P0 阶段 yfinance 实测拉取）承载
MACRO_SOURCES: dict[str, MacroSourceMeta] = {
    "VIX": MacroSourceMeta(
        symbol="VIX", yahoo_ticker="^VIX", field="vix",
        description="CBOE Volatility Index（标普500隐含波动率）", unit="index",
        scale=1.0, notes="值 >0；单位是指数点位，非百分比"),
    "US5Y": MacroSourceMeta(
        symbol="US5Y", yahoo_ticker="^FVX", field="us5y",
        description="美国5年期国债收益率", unit="percent",
        scale=1.0, notes="收益率以百分比数值存储（5.03 = 5.03%），非 bp"),
    "US10Y": MacroSourceMeta(
        symbol="US10Y", yahoo_ticker="^TNX", field="us10y",
        description="美国10年期国债收益率", unit="percent",
        scale=1.0, notes="收益率以百分比数值存储；^TNX 的 Yahoo 报价约等于 CBOE 10Y yield"),
    "DXY": MacroSourceMeta(
        symbol="DXY", yahoo_ticker="DX-Y.NYB", field="dxy",
        description="美元指数（Dollar Index）", unit="index",
        scale=1.0, notes="ICE 美元指数，基准 100"),
    "WTI": MacroSourceMeta(
        symbol="WTI", yahoo_ticker="CL=F", field="wti",
        description="WTI 原油近月期货结算价", unit="usd_per_barrel",
        scale=1.0, notes="2020-04-20 曾出现负油价 -37.63，真实值非数据错误"),
}

MACRO_SYMBOLS = set(MACRO_SOURCES.keys())

# 内部 symbol → OpenD code
SYMBOL_ALIASES = {"SPY": "US.SPY", "US.SPY": "US.SPY"}
