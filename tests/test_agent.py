from pathlib import Path
import tempfile
import unittest

from agent_brief.agent import Source, extract_findings, plan, render_markdown, run, write_result


class AgentTests(unittest.TestCase):
    def test_plan_rejects_invalid_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "http\\(s\\)"):
            plan("What changed?", ["file:///secret.txt"])


    def test_agent_keeps_claims_cited_and_records_failures(self) -> None:
        def fake_fetch(url: str) -> Source:
            if url.endswith("bad"):
                raise OSError("offline")
            return Source(url=url, title="Release note", text="The 2026 release improves offline reliability. It also shortens startup time.")

        result = run("What improves offline reliability?", ["https://example.test/good", "https://example.test/bad"], fetch=fake_fetch)
        self.assertTrue(result["findings"])
        self.assertEqual(result["errors"], [{"url": "https://example.test/bad", "error": "offline"}])
        self.assertIn("[Source 1]", render_markdown(result))
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "brief"
            write_result(out, result)
            self.assertTrue((out / "brief.md").is_file())
            self.assertTrue((out / "run.json").is_file())


    def test_finding_selection_uses_question_terms(self) -> None:
        source = Source(url="https://example.test", title="Test", text="A separate topic is discussed. Offline reliability improved through retries.")
        findings = extract_findings("How did offline reliability improve?", [source])
        self.assertEqual(findings[0].claim, "Offline reliability improved through retries.")


if __name__ == "__main__":
    unittest.main()

