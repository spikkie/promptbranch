from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "chatgpt_claudecode_workflow_release_control.sh").read_text(encoding="utf-8")


def test_v01041_through_v01045_force_fresh_direct_and_independent_localhost() -> None:
    assert 'if [[ "${ver}" == "v0.1.104.1" || "${ver}" == "v0.1.104.2" || "${ver}" == "v0.1.104.3" || "${ver}" == "v0.1.104.4" || "${ver}" == "v0.1.104.5" ]]' in SCRIPT
    assert 'force_fresh_full_transport_evidence=1' in SCRIPT
    assert '"${label}" == "direct" && ${force_fresh_full_transport_evidence} -eq 0' in SCRIPT
    assert 'full_direct_validation_evidence_reuse: forbidden' in SCRIPT
    assert 'full_localhost_policy: independent_execution_required' in SCRIPT
    assert 'full_localhost_direct_evidence_reuse: forbidden' in SCRIPT


def test_release_evidence_signature_contains_manifest_hash() -> None:
    assert 'release_validation_manifest_sha256()' in SCRIPT
    assert '--release-validation-manifest-sha256=%s' in SCRIPT
    assert '--fresh-full-transport-evidence=%s' in SCRIPT


def test_run_all_has_explicit_tenth_sandbox_gate() -> None:
    assert 'total=$((total + 8))' in SCRIPT
    assert 'run_all_json_step "sandbox_mutation_rollback_gate"' in SCRIPT
    assert 'scripts/verify-sandbox-mutation-rollback-release-gate.py' in SCRIPT
    assert 'sandbox_mutation_rollback_gate: $(summary_value' in SCRIPT
