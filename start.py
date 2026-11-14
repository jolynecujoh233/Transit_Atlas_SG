"""Bootstrap the recipient's private Python environment and run the local workbench."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def unpack_compressed_data():
    """Auto-decompress any *.geojson.zip datasets on fresh git clones."""
    import zipfile
    data_dir = ROOT / "data"
    if not data_dir.is_dir():
        return
    for zip_file in data_dir.rglob("*.geojson.zip"):
        geojson_target = zip_file.with_name(zip_file.name[:-4])
        if not geojson_target.exists():
            print(f"Decompressing {zip_file.name}...", flush=True)
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(zip_file.parent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8764)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check dependencies and Codex sign-in only")
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Please run with Python 3.12: py -3.12 start.py (Windows) or python3.12 start.py.")
    if not 0 <= args.port <= 65535:
        parser.error("port must be in range 0..65535")
    os.chdir(ROOT)
    envdir = ROOT / ".venv"
    py = envdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirements = ROOT / "requirements.txt"
    stamp = envdir / "transit-requirements.sha256"
    digest = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not py.is_file():
        print("Creating project environment...", flush=True)
        venv.EnvBuilder(with_pip=True).create(envdir)
    if not stamp.exists() or stamp.read_text().strip() != digest:
        subprocess.run([str(py), "-m", "pip", "install", "--only-binary=:all:", "-r", str(requirements)], check=True)
        stamp.write_text(digest)
    unpack_compressed_data()
    if Path(sys.prefix).resolve() != envdir.resolve():
        return subprocess.call([str(py), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.path.insert(0, str(ROOT / "workbench"))
    import server
    from research_agent import locate_codex, catalog
    cli = locate_codex()
    if not cli:
        raise SystemExit("Codex CLI not found. Install it and reopen your terminal; see the included guide.")
    auth = subprocess.run([cli, "login", "status"], check=False)
    if auth.returncode:
        raise SystemExit("Sign in to your own account with codex login, then restart.")
    count = len(catalog()[0])
    if args.check:
        print(f"Ready: {count} indicators, {server.info(server.FINISHED)['candidate_count']} example candidates.")
        return 0
    command = [sys.executable, str(ROOT / "workbench/server.py"), "--port", str(args.port)]
    if not args.no_browser:
        command.append("--open")
    return subprocess.call(command)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass
    except (subprocess.CalledProcessError, OSError) as error:
        sys.exit(str(error))

