import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCRAReportScript(unittest.TestCase):
    def test_review_required_does_not_fail_script(self):
        repo_root = Path(__file__).resolve().parents[1]
        script = repo_root / ".github" / "scripts" / "generate_cra_report.py"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            report_dir = tmp_path / "report"
            report_dir.mkdir()

            (report_dir / "sbom.spdx.json").write_text(
                json.dumps({"spdxVersion": "SPDX-2.3", "packages": []}),
                encoding="utf-8",
            )
            (report_dir / "code-scanning-open.json").write_text(
                json.dumps([{"number": 1, "rule": {"security_severity_level": "high"}}]),
                encoding="utf-8",
            )
            (report_dir / "code-scanning-dismissed.json").write_text("[]", encoding="utf-8")
            (report_dir / "dependabot-open.json").write_text("[]", encoding="utf-8")
            (report_dir / "dependabot-dismissed.json").write_text("[]", encoding="utf-8")
            (report_dir / "secret-scanning-open.json").write_text("[]", encoding="utf-8")
            (report_dir / "secret-scanning-resolved.json").write_text("[]", encoding="utf-8")
            (report_dir / "pip-packages.json").write_text("[]", encoding="utf-8")

            env = os.environ.copy()
            env.update(
                {
                    "GH_REPO": "cliquot22/TheiaMCR",
                    "GH_REF": "v0.0.0-test",
                    "GH_SHA": "0123456789abcdef",
                    "GH_RUN_ID": "1",
                }
            )

            run = subprocess.run(
                [sys.executable, str(script)],
                cwd=tmp_path,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)
            self.assertIn("Status:     REVIEW REQUIRED", run.stdout)
            self.assertTrue((report_dir / "cra-evidence-report.html").exists())


if __name__ == "__main__":
    unittest.main()
