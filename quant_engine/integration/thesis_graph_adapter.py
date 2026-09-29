# -*- coding: utf-8 -*-
"""final_state（TradingAgents 多 Agent 输出）→ CandidateThesis adapter（STEP 5.9-D）。

TradingAgents 的最终决策是自由文本（Rating + Summary + reports）。此 adapter 用一次
LLM 结构化调用把它提炼成 CandidateThesis，再走既有 parse_candidate → assemble_thesis
→ validate_thesis 链路。量化数值（probability/regime/lineage/version）仍由系统注入，
LLM 只负责把多 Agent 研究文本归纳成 6 字段。
"""
from __future__ import annotations

from .thesis_llm_adapter import CandidateThesis, parse_candidate, assemble_thesis
from .thesis import DirectionalBias


FINAL_STATE_TO_CANDIDATE_PROMPT = (
    "You are converting multi-agent research output into a structured trading thesis.\n"
    "STRICT RULES:\n"
    "1. Only cite data present in the QuantContext. Values marked NOT_AVAILABLE must be "
    "treated as NOT_AVAILABLE — never as 0, neutral, or bullish/bearish evidence.\n"
    "2. Confidence is NOT probability. Do NOT interpret confidence as P(price up).\n"
    "3. The UP/FLAT/DOWN probabilities are supplied by the system — do NOT output your own.\n"
    "4. Map the research consensus to directional_bias: bullish / bearish / neutral / mixed.\n\n"
    "Return valid JSON with exactly these fields:\n"
    '{"directional_bias":"bullish"|"bearish"|"neutral"|"mixed", '
    '"thesis_summary":"<1-3 sentences>", '
    '"confidence_score":<0-1 evidence consistency, NOT probability>, '
    '"confidence_level":"high"|"medium"|"low", '
    '"supporting_evidence":[{"source_type":"feature"|"event"|"regime"|"probability"|"market", '
    '"source_id":"<id from QuantContext or report>", "statement":"<reasoning>"}], '
    '"contradicting_evidence":[...], '
    '"invalidation_conditions":["<falsifying condition>"]}'
)


def final_state_to_candidate(final_state: dict, quant_context: str,
                             client, model: str) -> CandidateThesis:
    """TradingAgents final_state → CandidateThesis（一次 LLM 结构化调用）。"""
    decision = final_state.get("final_trade_decision", "")
    reports = {
        "market": final_state.get("market_report", ""),
        "fundamentals": final_state.get("fundamentals_report", ""),
        "news": final_state.get("news_report", ""),
        "sentiment": final_state.get("sentiment_report", ""),
    }
    report_block = "\n\n".join(f"--- {k} report ---\n{v[:800]}" for k, v in reports.items() if v)

    user = f"QuantContext:\n{quant_context}\n\nResearch consensus:\n{decision}\n\n{report_block}"
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": FINAL_STATE_TO_CANDIDATE_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
        max_tokens=16000,
    )
    raw = resp.choices[0].message.content
    if not raw:
        rc = getattr(resp.choices[0].message, "reasoning_content", "") or ""
        raw = rc  # reasoning 模型可能把 JSON 放 reasoning_content
    return parse_candidate(raw)


def thesis_from_final_state(final_state: dict, state, horizon: str, quant_context: str,
                            client, model: str, run_id: str, provider: str,
                            prompt_version: str, agent_version: str, temperature: float | None):
    """final_state → CandidateThesis → TradingThesis（完整 5.9-D/E 链路）。"""
    candidate = final_state_to_candidate(final_state, quant_context, client, model)
    return assemble_thesis(candidate, state, horizon, run_id, provider, model,
                           prompt_version, agent_version, temperature)
