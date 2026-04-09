"""CLI tests for guide-scorer."""
import json
from pathlib import Path

from click.testing import CliRunner

from guide_scorer.cli import cli

FIXTURES = Path(__file__).parent / "fixtures"


class TestScoreCommand:
    def setup_method(self):
        self.runner = CliRunner()
        self.good = str(FIXTURES / "good_guide.txt")
        self.poor = str(FIXTURES / "poor_guide.txt")

    def test_score_exits_zero(self):
        result = self.runner.invoke(cli, ["score", self.good])
        assert result.exit_code == 0

    def test_score_json_flag(self):
        result = self.runner.invoke(cli, ["score", self.good, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "overall_score" in data
        assert "dimensions" in data

    def test_json_has_eight_dimensions(self):
        result = self.runner.invoke(cli, ["score", self.good, "--json"])
        data = json.loads(result.output)
        assert len(data["dimensions"]) == 8

    def test_json_file_key_present(self):
        result = self.runner.invoke(cli, ["score", self.good, "--json"])
        data = json.loads(result.output)
        assert "file" in data

    def test_score_output_written(self, tmp_path):
        out_file = tmp_path / "result.json"
        result = self.runner.invoke(cli, ["score", self.good, "--output", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "overall_score" in data

    def test_missing_file_error(self):
        result = self.runner.invoke(cli, ["score", "nonexistent.txt"])
        assert result.exit_code != 0


class TestBatchCommand:
    def setup_method(self):
        self.runner = CliRunner()
        self.fixtures_dir = str(FIXTURES)

    def test_batch_exits_zero(self):
        result = self.runner.invoke(cli, ["batch", self.fixtures_dir])
        assert result.exit_code == 0

    def test_batch_json_output(self):
        result = self.runner.invoke(cli, ["batch", self.fixtures_dir, "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 2  # good + poor + minimal

    def test_batch_json_each_has_score(self):
        result = self.runner.invoke(cli, ["batch", self.fixtures_dir, "--json"])
        data = json.loads(result.output)
        for item in data:
            assert "overall_score" in item

    def test_batch_json_written_to_file(self, tmp_path):
        out_file = tmp_path / "batch.json"
        result = self.runner.invoke(
            cli, ["batch", self.fixtures_dir, "--output", str(out_file)]
        )
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert isinstance(data, list)

    def test_empty_dir_exits_zero(self, tmp_path):
        result = self.runner.invoke(cli, ["batch", str(tmp_path)])
        assert result.exit_code == 0
