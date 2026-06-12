"""Tests for the `python -m sage_ini` command line (stats / lint / xref)."""

import pytest

from sage_ini.__main__ import main


class TestLintCommand:
    def test_clean_file_exits_zero(self, tmp_path, capsys):
        path = tmp_path / "ok.ini"
        path.write_text("Object Foo\n    BuildCost = 100\nEnd\n", encoding="utf-8")
        assert main(["lint", str(path)]) == 0

    def test_conversion_error_exits_one(self, tmp_path, capsys):
        path = tmp_path / "bad.ini"
        path.write_text("Object Foo\n    BuildCost = notanumber\nEnd\n", encoding="utf-8")

        assert main(["lint", str(path)]) == 1
        assert "conversion-error" in capsys.readouterr().out

    def test_missing_path_errors(self, tmp_path, capsys):
        with pytest.raises(SystemExit):
            main(["lint", str(tmp_path / "nope.ini")])


class TestXrefCommand:
    def _folder(self, tmp_path):
        (tmp_path / "a.ini").write_text(
            "Upgrade Upgrade_Foo\nEnd\nCommandButton Command_Bar\n    Upgrade = Upgrade_Foo\nEnd\n",
            encoding="utf-8",
        )
        return tmp_path

    def test_reports_both_directions(self, tmp_path, capsys):
        root = self._folder(tmp_path)
        assert main(["xref", str(root), "Upgrade_Foo"]) == 0

        out = capsys.readouterr().out
        assert "Upgrade_Foo [upgrades]" in out
        assert "Command_Bar [commandbuttons]" in out

    def test_unknown_name_exits_one(self, tmp_path, capsys):
        root = self._folder(tmp_path)
        assert main(["xref", str(root), "DoesNotExist"]) == 1
        assert "no definition named" in capsys.readouterr().out
