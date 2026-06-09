from agent_cost_attribution import ledger


def _run():
    """A synthetic run mirroring the real wf_*.json schema: phase headers + agent rows."""
    return {
        "runId": "wf_test", "workflowName": "deep-research", "status": "completed",
        "totalTokens": 1000,
        "workflowProgress": [
            {"type": "workflow_phase", "index": 0, "title": "Scope"},
            {"type": "workflow_agent", "agentId": "a1", "label": "scope", "model": "claude-opus-4-8",
             "phaseTitle": "Scope", "state": "done", "tokens": 100, "toolCalls": 1},
            {"type": "workflow_phase", "index": 1, "title": "Verify"},
            {"type": "workflow_agent", "agentId": "a2", "label": "verify:0", "model": "claude-opus-4-8",
             "phaseTitle": "Verify", "state": "done", "tokens": 600, "toolCalls": 1},
            {"type": "workflow_agent", "agentId": "a3", "label": "verify:1", "model": "claude-opus-4-8",
             "phaseTitle": "Verify", "state": "error", "tokens": 300, "toolCalls": 0},
        ],
    }


def test_agents_skips_phase_headers():
    ags = ledger.agents(_run())
    assert [a.stage for a in ags] == ["Scope", "Verify", "Verify"]
    assert ags[0].tokens == 100 and ags[0].state == "done"


def test_decompose_sums_per_stage_in_order():
    assert ledger.decompose(_run()) == {"Scope": 100, "Verify": 900}


def test_invariant_holds_when_sum_matches_total():
    assert ledger.verify_invariant(_run()) is True


def test_invariant_fails_when_sum_mismatches_total():
    r = _run(); r["totalTokens"] = 999
    assert ledger.verify_invariant(r) is False


def test_summary_reports_pct_count_and_states():
    s = ledger.summary(_run())
    assert s["total_tokens"] == 1000 and s["invariant_ok"] is True
    assert s["stages"]["Verify"]["tokens"] == 900
    assert s["stages"]["Verify"]["pct"] == 90.0
    assert s["stages"]["Verify"]["states"] == {"done": 1, "error": 1}


def test_load_run_failsoft_on_missing(tmp_path):
    assert ledger.load_run(tmp_path / "nope.json") == {}


def test_agents_failsoft_on_bad_token_type():
    r = {"totalTokens": 0, "workflowProgress": [
        {"type": "workflow_agent", "phaseTitle": "X", "tokens": "bad", "state": "done", "toolCalls": 0},
    ]}
    ags = ledger.agents(r)
    assert len(ags) == 1 and ags[0].tokens == 0   # coerced, not crashed


def test_invariant_false_on_run_with_no_agent_rows():
    assert ledger.verify_invariant({"totalTokens": 0, "workflowProgress": []}) is False
    assert ledger.verify_invariant({}) is False
