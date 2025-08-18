# Tests for GitHub Actions workflow configuration related to qwiet.ai ShiftLeft integration.
# Testing framework: pytest (function-based tests with plain assertions).
# These tests validate critical configuration values from the workflow diff.
import re
from pathlib import Path
from typing import List

def _find_workflow_candidates() -> List[Path]:
    root = Path(".")
    workflows_dir = root / ".github" / "workflows"
    candidates: List[Path] = []
    if workflows_dir.exists():
        for p in workflows_dir.rglob("*.yml"):
            candidates.append(p)
        for p in workflows_dir.rglob("*.yaml"):
            candidates.append(p)
    return candidates

def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        # Fallback with default encoding if needed
        return p.read_text()

def _find_target_workflow_by_markers() -> Path | None:
    # Prefer a workflow with explicit name: qwiet.ai and job NextGen-Static-Analysis
    markers = [
        r"^name:\s*qwiet\.ai\s*$",
        r"\bNextGen-Static-Analysis\b",
    ]
    candidates = _find_workflow_candidates()
    for c in candidates:
        text = _read_text(c)
        if all(re.search(m, text, flags=re.M) for m in markers):
            return c
    # Fallback: any file mentioning NextGen-Static-Analysis
    for c in candidates:
        text = _read_text(c)
        if re.search(r"\bNextGen-Static-Analysis\b", text):
            return c
    return None

def _get_target_workflow_or_skip(pytest):
    p = _find_target_workflow_by_markers()
    if p is None:
        pytest.skip("No suitable GitHub Actions workflow found to validate (qwiet.ai / NextGen-Static-Analysis).")
    return p

def test_workflow_contains_expected_top_level_triggers(pytest):
    """
    Ensures the workflow is configured to run on pull_request and workflow_dispatch.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    # Using simple regex to check presence regardless of indentation specificities.
    assert re.search(r"^\s*on:\s*$", text, flags=re.M), "Missing 'on:' section"
    assert re.search(r"^\s*pull_request:\s*$", text, flags=re.M), "Workflow should trigger on pull_request"
    assert re.search(r"^\s*workflow_dispatch:\s*$", text, flags=re.M), "Workflow should allow manual dispatch"

def test_workflow_has_expected_job_name_and_runner(pytest):
    """
    Verify the job 'NextGen-Static-Analysis' exists and targets ubuntu-latest runner.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    assert "NextGen-Static-Analysis:" in text, "Missing job 'NextGen-Static-Analysis'"
    assert re.search(r"^\s*runs-on:\s*ubuntu-latest\s*$", text, flags=re.M), "Job should run on ubuntu-latest"

def test_checkout_and_shiftleft_cli_download_step_present(pytest):
    """
    Ensure checkout action and ShiftLeft CLI download are configured as per diff.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    assert re.search(r"uses:\s*actions/checkout@v3", text), "Expected actions/checkout@v3 step"
    # Validate CLI download and permissions
    assert "curl https://cdn.shiftleft.io/download/sl > ${GITHUB_WORKSPACE}/sl" in text, "Missing CLI download curl command"
    assert "chmod a+rx ${GITHUB_WORKSPACE}/sl" in text, "Missing chmod for CLI"

def test_prezero_static_analysis_step_commands(pytest):
    """
    Validate core commands in the 'preZero Static Analysis' step, including strictness and app/tag flags.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    # Ensure pip install of requirements
    assert re.search(r"^\s*pip install -r requirements\.txt\s*$", text, flags=re.M), "Must install Python requirements"
    # CLI version invocation
    assert re.search(r"\$\{GITHUB_WORKSPACE\}/sl --version", text), "Expected SL CLI version check"
    # Analyze command with strict & wait
    assert re.search(r"\$\{GITHUB_WORKSPACE\}/sl analyze --strict --wait", text), "Expected strict/wait flags for analyze"
    # App name
    assert re.search(r"--app\s+two-tier-flask-app", text), "Expected app name 'two-tier-flask-app'"
    # Tag branch param with GitHub expression
    assert re.search(r"--tag\s+branch=\$\{\{\s*github\.head_ref\s*\}\}", text), "Expected tag branch using github.head_ref"
    # Python source set to current working directory
    assert re.search(r"--pythonsrc\s+\$\((?:pwd)\)", text), "Expected --pythonsrc $(pwd)"

def test_expected_environment_variables_are_set(pytest):
    """
    Validate that required ShiftLeft environment variables are provided with correct values.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)

    # Access token via secrets
    assert re.search(
        r"SHIFTLEFT_ACCESS_TOKEN:\s*\$\{\{\s*secrets\.SHIFTLEFT_ACCESS_TOKEN\s*\}\}",
        text
    ), "SHIFTLEFT_ACCESS_TOKEN should be sourced from GitHub secrets"

    # Hosts
    assert re.search(r"SHIFTLEFT_API_HOST:\s*www\.shiftleft\.io", text), "Expected SHIFTLEFT_API_HOST=www.shiftleft.io"
    assert re.search(r"SHIFTLEFT_GRPC_TELEMETRY_HOST:\s*telemetry\.shiftleft\.io:443", text), "Expected telemetry host"
    assert re.search(r"SHIFTLEFT_GRPC_API_HOST:\s*api\.shiftleft\.io:443", text), "Expected gRPC API host"

def test_optional_build_rules_section_commented(pytest):
    """
    The diff shows an optional Build-Rules job commented out.
    We assert that if present, it remains commented (not active).
    This is a loose check that tolerates absence but enforces comment marker if present.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    # If "Build-Rules:" appears at all, ensure it's commented in the same line.
    # We allow optional leading spaces before the comment marker.
    occurrences = re.findall(r"(?m)^\s*#\s*Build-Rules:", text)
    # Either it's not present, or present only as a commented line.
    if "Build-Rules:" in text:
      assert len(occurrences) >= 1, "Build-Rules job appears to be active; expected it to be commented out per diff."

def test_workflow_name_is_expected(pytest):
    """
    Verify top-level workflow name is 'qwiet.ai' as per the provided configuration.
    """
    p = _get_target_workflow_or_skip(pytest)
    text = _read_text(p)
    assert re.search(r"(?m)^\s*name:\s*qwiet\.ai\s*$", text), "Workflow top-level name should be 'qwiet.ai'"

if __name__ == "__main__":
    # Simple manual debug runner: prints discovered candidate workflows.
    print("Candidate workflow files under .github/workflows:")
    for p in _find_workflow_candidates():
        print(" -", p)