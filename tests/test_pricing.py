from agent_cost_attribution import pricing


def test_opus_costs_more_than_haiku_for_same_tokens():
    assert pricing.estimate_cost(1_000_000, "claude-opus-4-8") > \
           pricing.estimate_cost(1_000_000, "claude-haiku-4-5-20251001")


def test_blended_rate_endpoints_match_list_prices():
    assert abs(pricing.blended_rate("claude-opus-4-8", input_share=1.0) - 15.0 / 1_000_000) < 1e-15
    assert abs(pricing.blended_rate("opus", input_share=0.0) - 75.0 / 1_000_000) < 1e-15


def test_unknown_model_priced_as_opus():
    assert pricing.estimate_cost(1000, "some-future-model") == pricing.estimate_cost(1000, "claude-opus-4-8")


def test_cost_by_stage_reflects_per_agent_model():
    run = {"totalTokens": 200, "workflowProgress": [
        {"type": "workflow_agent", "phaseTitle": "Fetch", "state": "done", "tokens": 100,
         "model": "claude-haiku-4-5-20251001", "toolCalls": 0},
        {"type": "workflow_agent", "phaseTitle": "Verify", "state": "done", "tokens": 100,
         "model": "claude-opus-4-8", "toolCalls": 0},
    ]}
    c = pricing.cost_by_stage(run)
    assert c["Verify"] > c["Fetch"]            # same tokens, opus dearer than haiku
    assert abs(pricing.total_cost(run) - (c["Verify"] + c["Fetch"])) < 1e-15


def test_opus_full_run_estimate_is_in_expected_band():
    # 1,000,000 opus tokens at 85% input ≈ $24 (0.85*15 + 0.15*75 = 24)
    est = pricing.estimate_cost(1_000_000, "claude-opus-4-8")
    assert 23.9 < est < 24.1
