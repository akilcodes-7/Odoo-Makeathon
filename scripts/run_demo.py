"""Prepare a persistent evaluator workspace and run Brightloop on localhost."""

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / ".demo"
ACCOUNTS = (
    "admin@brightloop.test",
    "staff@brightloop.test",
    "customer@brightloop.test",
    "customer2@brightloop.test",
)


def private_write(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--prepare-only", action="store_true", help="Set up accounts/data without starting the server.")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Use Python 3.12 or newer to start this project.")
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")

    python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creating the project's Python environment…", flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")

    if subprocess.run([str(python), "-m", "pip", "--version"], capture_output=True).returncode:
        subprocess.run([str(python), "-m", "ensurepip", "--upgrade"], cwd=ROOT, check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", "-r", str(ROOT / "requirements.txt")], cwd=ROOT, check=True)
    DEMO.mkdir(mode=0o700, exist_ok=True)
    config_path = DEMO / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        config = {
            "secret_key": secrets.token_urlsafe(64),
            "password": os.environ.get("BRIGHTLOOP_DEMO_PASSWORD") or "Demo!" + secrets.token_urlsafe(18),
        }
        private_write(config_path, json.dumps(config))

    database = DEMO / "db.sqlite3"
    initialized = DEMO / "initialized"
    needs_seed = not initialized.exists() or not database.exists()
    env = dict(os.environ)
    env.update({
        "DATABASE_PATH": str(database),
        "SECRET_KEY": config["secret_key"],
        "BRIGHTLOOP_DEMO_PASSWORD": config["password"],
        "DEBUG": "true",
        "ALLOWED_HOSTS": "localhost,127.0.0.1,[::1]",
        "EMAIL_BACKEND": "django.core.mail.backends.filebased.EmailBackend",
        "EMAIL_FILE_PATH": str(DEMO / "emails"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })

    def manage(*arguments):
        subprocess.run([str(python), "manage.py", *arguments], cwd=ROOT, env=env, check=True)

    manage("migrate", "--noinput")
    if needs_seed:
        manage("seed_evaluation", "--noinput")
        private_write(DEMO / "access.txt", "Brightloop local evaluator accounts\n\n" + "\n".join(ACCOUNTS)
                      + "\n\nShared password for this local installation: " + config["password"]
                      + "\n\nThese are local demonstration accounts. Do not commit this file.\n")
        private_write(initialized, "Demo data initialized; later launches preserve evaluator changes.\n")
    manage("check")
    print(f"\nBrightloop: http://127.0.0.1:{args.port}/", flush=True)
    print(f"Account emails and password: {DEMO / 'access.txt'}", flush=True)
    print(f"Database: {database} (retained between launches)", flush=True)
    print(f"Invoice/reset emails: {DEMO / 'emails'} (local files; no external delivery)", flush=True)
    print("Walkthrough: docs/EVALUATOR_GUIDE.md\n", flush=True)
    if not args.prepare_only:
        manage("runserver", f"127.0.0.1:{args.port}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBrightloop stopped. Demo data is saved.")
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
