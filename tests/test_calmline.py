import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(REPO, "plugin")
sys.path.insert(0, ROOT)
import calmline  # noqa: E402

ANSI = re.compile(r"\033\[[0-9;]*m")


def fixture(name):
    with open(os.path.join(ROOT, "fixtures", name)) as f:
        return json.load(f)


def plain(lines):
    return [ANSI.sub("", line) for line in lines]


class CalmlineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["CALMLINE_STATE"] = os.path.join(self.tmp.name, "turn.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_input_renders_both_lines(self):
        top, bottom = plain(calmline.render(fixture("full.json")))
        self.assertIn("Fix login redirect", top)
        self.assertIn("Opus 5.5 · medium", top)
        self.assertIn("ctx 23%", top)
        self.assertIn("cache 97%", top)
        self.assertIn("$1.84", bottom)
        self.assertIn("5h 37%", bottom)
        self.assertIn("week 62%", bottom)

    def test_missing_data_hides_segments_instead_of_failing(self):
        lines = plain(calmline.render(fixture("minimal.json")))
        self.assertTrue(lines[0].startswith("Sonnet 5.5"))
        self.assertNotIn("5h", "".join(lines))
        self.assertNotIn("!", "".join(lines))

    def test_no_rate_limits_drops_only_the_limits(self):
        bottom = plain(calmline.render(fixture("no-limits.json")))[1]
        self.assertIn("$1.84", bottom)
        self.assertNotIn("5h", bottom)

    def test_thresholds_colour_the_number(self):
        self.assertIn("\033[32m", calmline.level(10, 50, 80))
        self.assertIn("\033[33m", calmline.level(50, 50, 80))
        self.assertIn("\033[31m", calmline.level(80, 50, 80))

    def test_last_turn_is_the_change_between_prompt_starts(self):
        d = fixture("full.json")
        calmline.render(d)
        d["cost"] = {"total_cost_usd": 2.01, "total_api_duration_ms": 412000 + 26000}
        calmline.render(d)  # still the same prompt: totals grow, nothing to report yet
        d["prompt_id"] = "p2"
        bottom = plain(calmline.render(d))[1]
        self.assertIn("last $0.17 · 26s", bottom)

    def test_broken_segment_shows_marker_and_others_still_render(self):
        def boom(_):
            raise ValueError("bug")

        segments = {**calmline.SEGMENTS, "boom": boom}
        line = plain(calmline.render(fixture("full.json"), segments, [["model", "boom"]]))[0]
        self.assertIn("Opus 5.5", line)
        self.assertIn("boom !", line)

    def test_slow_segment_is_cut_off(self):
        segments = {**calmline.SEGMENTS, "slow": lambda _: time.sleep(2) or "late"}
        start = time.monotonic()
        line = plain(calmline.render(fixture("full.json"), segments, [["slow"]]))[0]
        self.assertLess(time.monotonic() - start, 1)
        self.assertEqual(line, "slow …")

    def test_without_git_installed_the_branch_is_just_hidden(self):
        d = {**fixture("full.json"), "cwd": ROOT}
        path = os.environ["PATH"]
        os.environ["PATH"] = "/nonexistent"
        try:
            top = plain(calmline.render(d))[0]
        finally:
            os.environ["PATH"] = path
        self.assertNotIn("git", top)

    def test_dir_shortens_home_and_long_paths(self):
        home = os.path.expanduser("~")
        dir_of = lambda cwd: plain([calmline.directory({"cwd": cwd})])[0]
        self.assertEqual(dir_of(home), "~")
        self.assertEqual(dir_of(os.path.join(home, "dev", "app")), "~/dev/app")
        self.assertEqual(dir_of(os.path.join(home, "dev", "app", "mobile", "src")), "mobile/src")
        self.assertEqual(dir_of("/opt"), "/opt")
        self.assertIsNone(calmline.directory({}))

    def test_unknown_segment_name_is_visible(self):
        line = plain(calmline.render(fixture("full.json"), lines=[["model", "typo"]]))[0]
        self.assertIn("typo ?", line)

    def test_until_formats_minutes_hours_days(self):
        self.assertEqual(calmline.until(100 + 45 * 60, now=100), "45m")
        self.assertEqual(calmline.until(100 + 98 * 60, now=100), "1h38")
        self.assertEqual(calmline.until(100 + (2 * 1440 + 180) * 60, now=100), "2d3h")

    def test_example_custom_segments_load_and_render(self):
        os.environ["VIRTUAL_ENV"] = "/work/.venvs/api"
        try:
            extra, lines = calmline.load_custom(os.path.join(ROOT, "my_segments.example.py"))
            top = plain(calmline.render(fixture("full.json"), {**calmline.SEGMENTS, **extra}, lines))[0]
        finally:
            del os.environ["VIRTUAL_ENV"]
        self.assertTrue(top.endswith("venv api"))

    def test_install_script_sets_status_line_and_keeps_the_previous_one(self):
        home = os.path.join(self.tmp.name, "home")
        os.makedirs(os.path.join(home, ".claude"))
        settings = os.path.join(home, ".claude", "settings.json")
        with open(settings, "w") as f:
            json.dump({"theme": "dark", "statusLine": {"type": "command", "command": "~/old.sh"}}, f)
        env = {**os.environ, "HOME": home, "CALMLINE_SRC": "file://" + REPO}
        for _ in range(2):  # a reinstall must not overwrite the saved original
            subprocess.run(["sh", os.path.join(REPO, "install.sh")], env=env, check=True, capture_output=True)
        with open(settings) as f:
            data = json.load(f)
        self.assertEqual(data["theme"], "dark")
        self.assertTrue(data["statusLine"]["command"].endswith("/.claude/calmline/calmline.py"))
        with open(os.path.join(home, ".claude", "calmline", "previous-statusline.json")) as f:
            self.assertEqual(json.load(f)["command"], "~/old.sh")

    def test_install_script_from_a_git_clone_only_sets_the_status_line(self):
        home = os.path.join(self.tmp.name, "home")
        dest = os.path.join(home, ".claude", "calmline")
        subprocess.run(["git", "clone", "-q", REPO, dest], check=True)
        env = {**os.environ, "HOME": home, "CALMLINE_SRC": "file:///nonexistent"}  # any download would fail
        subprocess.run(["sh", os.path.join(dest, "install.sh")], env=env, check=True, capture_output=True)
        with open(os.path.join(home, ".claude", "settings.json")) as f:
            self.assertTrue(json.load(f)["statusLine"]["command"].endswith("/.claude/calmline/plugin/calmline.py"))

    def test_update_hook_refreshes_the_copy_but_not_my_segments(self):
        dest = os.path.join(self.tmp.name, "home", ".claude", "calmline")
        os.makedirs(dest)
        for name, text in (("calmline.py", "# old"), ("my_segments.py", "mine")):
            with open(os.path.join(dest, name), "w") as f:
                f.write(text)
        env = {**os.environ, "HOME": os.path.join(self.tmp.name, "home"), "CLAUDE_PLUGIN_ROOT": ROOT}
        subprocess.run(["sh", os.path.join(ROOT, "hooks", "update.sh")], env=env, check=True)
        with open(os.path.join(dest, "calmline.py")) as f, open(os.path.join(ROOT, "calmline.py")) as g:
            self.assertEqual(f.read(), g.read())
        with open(os.path.join(dest, "my_segments.py")) as f:
            self.assertEqual(f.read(), "mine")

    def test_cli_reads_stdin(self):
        with open(os.path.join(ROOT, "fixtures", "full.json")) as f:
            out = subprocess.run(
                [sys.executable, os.path.join(ROOT, "calmline.py")], stdin=f, capture_output=True, text=True, check=True
            ).stdout
        self.assertEqual(len(out.strip().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
