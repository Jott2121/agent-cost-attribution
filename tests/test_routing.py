"""Tests for the routing module — role table, fail-soft overrides, per-message routing."""
import json

import pytest

from agent_cost_attribution.routing import MessageRouter, Router, savings_estimate

ROLES = {
    "chat":      {"model": "claude-sonnet-4-6", "effort": "medium"},
    "chat_deep": {"model": "claude-fable-5", "effort": "high"},
    "extract":   {"model": "claude-haiku-4-5", "effort": None},
    "build":     {"model": "claude-fable-5", "effort": "xhigh"},
}

TAGS = {
    "deep":  {"model": "claude-fable-5", "effort": "high"},
    "cheap": {"model": "claude-haiku-4-5", "effort": None},
}


# --- Router: role table + overrides -------------------------------------------------


def test_resolve_returns_copy_of_default():
    r = Router(ROLES)
    cfg = r.resolve("chat")
    assert cfg == ROLES["chat"]
    cfg["model"] = "mutated"
    assert r.resolve("chat")["model"] == "claude-sonnet-4-6"   # table not mutated


def test_unknown_role_fails_closed():
    with pytest.raises(KeyError):
        Router(ROLES).resolve("typo_role")


def test_overrides_merge_partial(tmp_path):
    p = tmp_path / "routing.json"
    p.write_text(json.dumps({"chat": {"model": "claude-opus-4-8"}}))
    r = Router(ROLES, overrides_path=p)
    cfg = r.resolve("chat")
    assert cfg["model"] == "claude-opus-4-8"
    assert cfg["effort"] == "medium"            # untouched key keeps the default


def test_overrides_fail_soft_on_corrupt_or_missing(tmp_path):
    bad = tmp_path / "routing.json"
    bad.write_text("{not json")
    assert Router(ROLES, overrides_path=bad).resolve("chat") == ROLES["chat"]
    assert Router(ROLES, overrides_path=tmp_path / "nope.json").resolve("chat") == ROLES["chat"]


def test_overrides_ignore_garbage_values(tmp_path):
    p = tmp_path / "routing.json"
    p.write_text(json.dumps({"chat": {"model": 42}, "build": "nope"}))
    r = Router(ROLES, overrides_path=p)
    assert r.resolve("chat")["model"] == "claude-sonnet-4-6"
    assert r.resolve("build") == ROLES["build"]


def test_model_for_and_effort_for():
    r = Router(ROLES)
    assert r.model_for("extract") == "claude-haiku-4-5"
    assert r.effort_for("extract") is None


# --- MessageRouter: tag > escalation heuristic > cheap default ----------------------


def _mr(deep_pattern=r"(?:^|[.!?]\s+|\b(?:please|help me|let'?s)\s+)(?:debug|refactor|architect)\b"):
    return MessageRouter(Router(ROLES), tags=TAGS, deep_pattern=deep_pattern)


def test_plain_message_routes_to_default_role():
    cfg, text = _mr().route("what's on the calendar?")
    assert cfg == ROLES["chat"]
    assert text == "what's on the calendar?"


def test_deep_work_language_escalates():
    cfg, _ = _mr().route("debug the wedged daemon")
    assert cfg == ROLES["chat_deep"]


def test_noun_usage_does_not_escalate():
    cfg, _ = _mr().route("status of the debug session?")
    assert cfg == ROLES["chat"]


def test_tag_wins_and_is_stripped():
    cfg, text = _mr().route("!cheap debug the wedged daemon")
    assert cfg == TAGS["cheap"]
    assert text == "debug the wedged daemon"


def test_tag_case_insensitive_mid_message():
    cfg, text = _mr().route("please !DEEP weigh the options")
    assert cfg == TAGS["deep"]
    assert text == "please weigh the options"


def test_embedded_bang_word_is_not_a_tag():
    cfg, text = _mr().route("wow!cheap models are fine")
    assert cfg == ROLES["chat"]
    assert text == "wow!cheap models are fine"


def test_none_input_is_safe():
    cfg, text = _mr().route(None)
    assert cfg == ROLES["chat"]
    assert text == ""


# --- savings_estimate: the meter <-> router handshake -------------------------------


def test_savings_estimate_routed_vs_uniform_baseline():
    traffic = {"chat": 1_000_000, "extract": 1_000_000, "build": 1_000_000}
    est = savings_estimate(traffic, ROLES, baseline_model="claude-fable-5")
    # build is fable in BOTH scenarios -> contributes zero savings
    assert est["baseline_usd"] > est["routed_usd"]
    assert est["saved_usd"] == pytest.approx(est["baseline_usd"] - est["routed_usd"])
    assert 0 < est["saved_pct"] < 100


def test_savings_estimate_unknown_role_fails_closed():
    with pytest.raises(KeyError):
        savings_estimate({"typo": 1000}, ROLES, baseline_model="claude-fable-5")


def test_empty_tags_dict_never_crashes_on_bang_words():
    mr = MessageRouter(Router(ROLES), tags={}, deep_pattern=r"^debug\b")
    cfg, text = mr.route("!foo what about this?")
    assert cfg == ROLES["chat"]
    assert text == "!foo what about this?"


def test_overrides_path_accepts_str(tmp_path):
    p = tmp_path / "routing.json"
    p.write_text(json.dumps({"chat": {"model": "claude-opus-4-8"}}))
    assert Router(ROLES, overrides_path=str(p)).model_for("chat") == "claude-opus-4-8"
