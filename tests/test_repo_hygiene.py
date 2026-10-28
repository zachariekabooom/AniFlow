import os
import shutil
import string
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support.repo_hygiene import MAX_FILE_BYTES, RepoUnavailable, find_violations

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


class CurrentRepositoryTests(unittest.TestCase):
    @unittest.skipUnless(GIT and (ROOT / ".git").exists(), "git ou dépôt Git absents")
    def test_tracked_files_are_clean(self):
        try:
            problems = find_violations(ROOT)
        except RepoUnavailable as exc:
            self.skipTest(f"dépôt Git illisible : {exc}")
        self.assertEqual(problems, [], "fichiers suivis à retirer de Git (dépôt public) :\n" + "\n".join(problems))


@unittest.skipUnless(GIT, "git absent")
class DetectorTests(unittest.TestCase):
    def git(self, root, *args):
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        return subprocess.run([GIT, "-C", str(root), *args], capture_output=True, env=env, check=True)

    def make_repo(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.git(root, "init", "-q")
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        self.git(root, "add", "-A", "-f")  # -f : indifférent aux .gitignore globaux du poste
        return root

    def test_every_kind_of_forbidden_file_is_flagged_and_allowed_ones_are_not(self):
        real_looking_token = "ghp_" + (string.ascii_letters + string.digits)[:36]  # construit à l'exécution
        personal_path = "C:" + "\\Users\\" + "jean" + "\\Videos"
        forbidden = {
            "aniflow.db": b"x", "data.sqlite3": b"x", "reports/anilist.json": b"{}", "third_party/libmpv/libmpv-2.dll": b"x",
            "models/gemma.gguf": b"x", ".env": "A=1", ".env.local": "A=1", "video.mp4": b"x", "archive.zip": b"x",
            "src/aniflow/__pycache__/m.pyc": b"x", "big.bin": b"\0" * (MAX_FILE_BYTES + 1),
            "notes.txt": f"voici : {real_looking_token}\n", "perso.md": f"dossier {personal_path}\n",
        }
        allowed = {
            "reports/README.md": "local", "third_party/README.md": "local", ".env.example": "A=", "src/ok.py": "x = 1\n", "docs/guide.md": "Bonjour\n",
            "src/aniflow/services/downloads/__init__.py": "",  # un dossier « downloads » du code n'est pas le dossier racine local
        }
        root = self.make_repo({**forbidden, **allowed})
        report = "\n".join(find_violations(root))
        for rel in forbidden:
            self.assertIn(f"{rel} :", report, f"{rel} aurait dû être signalé")
        for rel in allowed:
            self.assertNotIn(f"{rel} :", report, f"{rel} ne doit pas être signalé")
        self.assertNotIn(real_looking_token, report)  # le secret n'est jamais reproduit
        self.assertNotIn("jean", report)

    def test_clean_repository_has_no_violation(self):
        root = self.make_repo({"src/ok.py": "x = 1\n", "README.md": "Bonjour\n", "reports/README.md": "local", ".env.example": "A="})
        self.assertEqual(find_violations(root), [])

    def test_placeholders_are_not_mistaken_for_secrets(self):
        text = ("ghp_" + "x" * 36 + "\n" + "sk-" + "a" * 30 + "\n" + "AKIA" + "0" * 16 + "\n" + "C:" + "\\Users\\<nom>\\Videos\n" + "%USERPROFILE%\\Videos\n")
        self.assertEqual(find_violations(self.make_repo({"exemple.md": text})), [])

    def test_only_the_current_index_is_examined_never_the_history(self):
        root = self.make_repo({"aniflow.db": b"x", "src/ok.py": "x = 1\n"})
        self.assertTrue(find_violations(root))
        commit = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
        self.git(root, *commit, "commit", "-q", "-m", "avec une base (historique)")
        self.git(root, "rm", "-q", "--cached", "aniflow.db")
        self.git(root, *commit, "commit", "-q", "-m", "retrait de la base")
        self.assertEqual(find_violations(root), [])  # l'historique contient encore la base : volontairement non audité
        (root / "autre.db").write_bytes(b"x")  # non suivi : ignoré
        self.assertEqual(find_violations(root), [])

    def test_a_folder_that_is_not_a_repository_is_reported_as_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RepoUnavailable):
            find_violations(Path(tmp))


if __name__ == "__main__":
    unittest.main()
