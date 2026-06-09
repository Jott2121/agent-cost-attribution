import json
from agent_cost_attribution import cli


def _run():
    return {"runId": "wf_x", "workflowName": "deep-research", "status": "completed",
            "totalTokens": 1000,
            "workflowProgress": [
                {"type": "workflow_agent", "phaseTitle": "Verify", "state": "done", "tokens": 900, "toolCalls": 1},
                {"type": "workflow_agent", "phaseTitle": "Scope", "state": "done", "tokens": 100, "toolCalls": 1},
            ]}


def test_render_lists_stages_largest_first_with_total():
    out = cli.render(_run())
    assert "total=1,000" in out
    assert out.index("Verify") < out.index("Scope")   # largest stage first


def test_render_warns_on_degraded_run():
    r = _run()
    r["workflowProgress"][0]["state"] = "error"
    out = cli.render(r)
    assert "DEGRADED" in out


def test_main_runs_over_a_directory(tmp_path):
    (tmp_path / "wf_a.json").write_text(json.dumps(_run()))
    assert cli.main([str(tmp_path)]) == 0


def test_main_no_args_is_usage_error():
    assert cli.main([]) == 2
