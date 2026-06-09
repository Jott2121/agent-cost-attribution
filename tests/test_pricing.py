from agent_cost_attribution import pricing


def test_opus_costs_more_than_haiku_for_same_tokens():
    assert pricing.estimate_cost(1_000_000, "claude-opus-4-8") > \
           pricing.estimate_cost(1_000_000, "claude-haiku-4-5-20251001")


def test_fable_is_the_premium_tier():
    # Claude Fable 5 = $10/$50 — pricier than Opus 4.8 ($5/$25); blended @85% input = $16/MTok
    assert pricing.estimate_cost(1_000_000, "claude-fable-5") > \
           pricing.estimate_cost(1_000_000, "claude-opus-4-8")
    assert abs(pricing.estimate_cost(1_000_000, "claude-fable-5") - 16.0) < 0.1


def test_blended_rate_endpoints_match_list_prices():
    assert abs(pricing.blended_rate("claude-opus-4-8", input_share=1.0) - 5.0 / 1_000_000) < 1e-15
    assert abs(pricing.blended_rate("opus", input_share=0.0) - 25.0 / 1_000_000) < 1e-15


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
    # 1,000,000 opus tokens at 85% input ≈ $8 (0.85*5 + 0.15*25 = 8)
    est = pricing.estimate_cost(1_000_000, "claude-opus-4-8")
    assert 7.9 < est < 8.1
