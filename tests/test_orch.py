"""lib/orch.py birim testleri (#372). Çalıştır: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ORCH = os.path.join(os.path.dirname(__file__), "..", "lib", "orch.py")


def run(*args, stdin=""):
    return subprocess.run(
        [sys.executable, ORCH, *args], input=stdin, capture_output=True, text=True
    )


def deploy_yml(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False)
    f.write(text)
    f.close()
    return f.name


VALID = """name: demo
git_url: https://github.com/omerfkara/demo.git
target_runner: pi
repo_path: /home/omer/demo
build_command: "cd /home/omer/demo && git pull"
deploy_command: "docker compose up -d"
watch_paths: backend/, Dockerfile
"""


class RegisterBody(unittest.TestCase):
    def test_valid_file_builds_body_and_splits_watch_paths(self):
        r = run("register", deploy_yml(VALID))
        self.assertEqual(r.returncode, 0, r.stderr)
        body = json.loads(r.stdout)
        self.assertEqual(body["name"], "demo")
        self.assertEqual(body["watch_paths"], ["backend/", "Dockerfile"])
        self.assertEqual(body["repo_path"], "/home/omer/demo")

    def test_missing_required_field_is_rejected(self):
        r = run("register", deploy_yml(VALID.replace('deploy_command: "docker compose up -d"\n', "")))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("deploy_command", r.stderr)

    def test_ssh_git_url_is_rejected(self):
        bad = VALID.replace("https://github.com/omerfkara/demo.git", "git@github.com:omerfkara/demo.git")
        self.assertNotEqual(run("register", deploy_yml(bad)).returncode, 0)

    def test_unknown_runner_and_relative_repo_path_are_rejected(self):
        self.assertNotEqual(run("register", deploy_yml(VALID.replace("target_runner: pi", "target_runner: mars"))).returncode, 0)
        self.assertNotEqual(run("register", deploy_yml(VALID.replace("/home/omer/demo\n", "demo\n"))).returncode, 0)


class StatusTable(unittest.TestCase):
    ROWS = [
        {"id": 388, "project": "duqme-admin", "target_runner": "pi", "status": "done",
         "triggered_by": "webhook", "git_sha": "681369023f6539ca1daae3c4a70c805906359e91",
         "created_at": "2026-10-04T11:45:18.925984+00:00"},
        {"id": 5, "project": "x", "target_runner": "macos", "status": "failed",
         "triggered_by": "catchup", "git_sha": "", "created_at": "2026-10-01T02:59:59+00:00"},
    ]

    def test_columns_short_sha_server_and_trigger(self):
        out = run("table", "10", stdin=json.dumps(self.ROWS)).stdout
        header, first, second = out.splitlines()[:3]
        self.assertEqual(header.split(), ["ID", "PROJECT", "SERVER", "STATUS", "TRIGGER", "SHA", "TIMESTAMP"])
        self.assertIn("6813690", first)
        self.assertNotIn("681369023", first)
        self.assertIn(" pi ", first)
        self.assertIn("2026-10-04 11:45:18", first)
        self.assertIn("catchup", second)

    def test_limit_and_empty(self):
        self.assertEqual(len(run("table", "1", stdin=json.dumps(self.ROWS)).stdout.splitlines()), 2)
        self.assertIn("kayıt yok", run("table", "5", stdin="[]").stdout)


class EnvBody(unittest.TestCase):
    def test_file_is_sent_as_is(self):
        body = json.loads(run("envbody", deploy_yml("# yorum\nA=1\n")).stdout)
        self.assertEqual(body, {"content": "# yorum\nA=1\n"})

    def test_file_without_variables_is_rejected(self):
        self.assertNotEqual(run("envbody", deploy_yml("# yalnız yorum\n")).returncode, 0)


if __name__ == "__main__":
    unittest.main()
