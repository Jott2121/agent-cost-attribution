from agent_cost_attribution import health


def _agent(stage, state, tokens):
    return {"type": "workflow_agent", "agentId": "x", "label": stage, "model": "m",
            "phaseTitle": stage, "state": state, "tokens": tokens, "toolCalls": 0}


def _healthy_run():
    rows = [_agent("Verify", "done", 8000) for _ in range(6)]
    rows += [_agent("Fetch", "done", 16000) for _ in range(5)]
    return {"totalTokens": 128000, "workflowProgress": rows}


def _broken_verify_run():
    # mirrors wf_3d01df61: 6 verifiers all errored at ~1588 tok, Fetch healthy
    rows = [_agent("Verify", "error", 1588) for _ in range(6)]
    rows += [_agent("Fetch", "done", 16000) for _ in range(5)]
    return {"totalTokens": 89528, "workflowProgress": rows}


def test_healthy_run_has_no_findings():
    assert health.detect_degradation(_healthy_run()) == []
    assert health.is_healthy(_healthy_run()) is True


def test_errored_stage_flagged():
    findings = health.detect_degradation(_broken_verify_run())
    kinds = {(f["stage"], f["kind"]) for f in findings}
    assert ("Verify", "errors") in kinds
    assert health.is_healthy(_broken_verify_run()) is False


def test_anomalously_cheap_stage_flagged_even_without_error_state():
    # a stage that 'succeeded' but ran far below the run-wide median is still degraded
    rows = [{"type": "workflow_agent", "phaseTitle": "Verify", "state": "done",
             "tokens": 1500, "toolCalls": 0} for _ in range(6)]
    rows += [{"type": "workflow_agent", "phaseTitle": "Fetch", "state": "done",
              "tokens": 16000, "toolCalls": 0} for _ in range(5)]
    findings = health.detect_degradation({"totalTokens": 89000, "workflowProgress": rows})
    assert any(f["stage"] == "Verify" and f["kind"] == "cheap" for f in findings)
