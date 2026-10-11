import json
import subprocess
import sys

from conftest import ROOT


def test_fixed_two_workspace_workflow_runs_downloaded_skill_and_records_full_dag(tmp_path):
    output = tmp_path / "acceptance"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_acceptance.py"), "--out", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    evidence = json.loads((output / "evidence.json").read_text())
    assert evidence["status"] == "passed"
    assert evidence["interfaces"] == ["real HTTP", "CLI subprocess"]
    assert evidence["skill_result"] == {
        "baseline_mean_ms": 12.0,
        "candidate_mean_ms": 9.0,
        "difference_ms": -3.0,
        "trials_per_variant": 3,
        "conclusion": "pilot_only",
    }
    ids = evidence["publications"]
    assert evidence["parents"] == {
        ids["root"]: [],
        ids["left"]: [ids["root"]],
        ids["right"]: [ids["root"]],
        ids["merge"]: [ids["left"], ids["right"]],
    }
    assert evidence["snapshot_unchanged"] is True
    assert evidence["private_canary_absent"] is True
    assert evidence["restart_preserved"] is True
    assert (output / "b/downloaded-skill/scripts/summarize.py").is_file()
    assert (output / "b/sharey-skill/SKILL.md").is_file()
    assert evidence["cross_vendor_agent_acceptance"] == "not exercised by this CLI runner"
