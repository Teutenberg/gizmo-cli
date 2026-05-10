import json
import os
import stat
import subprocess
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from .config import config_get


def _cfg(key: str, fallback):
    val = config_get(f"ollama.{key}")
    return val if val is not None else fallback


def ollama_host() -> str:
    return _cfg("host", "http://localhost:11434")


def ollama_model() -> str:
    return _cfg("model", "qwen2.5:3b")


def ollama_timeout() -> int:
    return int(_cfg("timeout", 120))


def ollama_system_installer_url() -> str:
    return _cfg("system_installer_url", "https://ollama.com/install.sh")


def ollama_user_binary_install_dir() -> Path:
    return Path(_cfg("user_binary_install_dir", "~/.local/bin")).expanduser()


def ollama_user_binary_url() -> str:
    return _cfg("user_binary_url", "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64")


def is_running() -> bool:
    try:
        with urllib.request.urlopen(ollama_host(), timeout=3):
            return True
    except Exception:
        return False


def install(user: bool = True) -> Path | None:
    """Install Ollama.

    user=True (default): download the binary to install_dir — no sudo needed.
    user=False: run the official install script (requires root).

    Returns the binary path for user installs, None for script installs.
    """
    if not user:
        result = subprocess.run(f"curl -fsSL {ollama_system_installer_url()} | sh", shell=True)
        if result.returncode != 0:
            raise RuntimeError("Ollama installation failed.")
        return None

    install_dir = ollama_user_binary_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)
    binary = install_dir / "ollama"
    url = ollama_user_binary_url()

    req = urllib.request.Request(url, headers={"User-Agent": "gizmo-cli"})
    with tempfile.NamedTemporaryFile(suffix=".tar.zst", delete=False) as tmp:
        tmp_path = tmp.name
        with urllib.request.urlopen(req) as resp:
            while chunk := resp.read(1 << 16):
                tmp.write(chunk)

    try:
        result = subprocess.run(
            ["tar", "--use-compress-program=unzstd", "-xf", tmp_path,
             "--strip-components=1", "-C", str(install_dir), "--wildcards", "*/ollama"],
            capture_output=True,
        )
        if result.returncode != 0:
            # fallback: extract all and find the binary
            subprocess.run(
                ["tar", "--use-compress-program=unzstd", "-xf", tmp_path, "-C", str(install_dir)],
                check=True,
            )
    finally:
        os.unlink(tmp_path)

    binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Warn if install_dir is not on PATH
    if str(install_dir) not in os.environ.get("PATH", "").split(":"):
        return binary  # caller will warn

    return binary


def _ollama_bin() -> str:
    """Return the ollama binary path, preferring the configured install dir."""
    candidate = ollama_user_binary_install_dir() / "ollama"
    if candidate.exists():
        return str(candidate)
    return "ollama"  # fall back to PATH


def run() -> subprocess.Popen:
    """Start the Ollama server in the background and return its process."""
    proc = subprocess.Popen(
        [_ollama_bin(), "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc


def pull(model: str | None = None) -> None:
    """Pull a model via the ollama CLI."""
    target = model or ollama_model()
    result = subprocess.run([_ollama_bin(), "pull", target])
    if result.returncode != 0:
        raise RuntimeError(f"Failed to pull model '{target}'.")


def status() -> dict:
    """Return basic status info about the local Ollama instance."""
    running = is_running()
    info = {"host": ollama_host(), "model": ollama_model(), "running": running}
    if running:
        try:
            with urllib.request.urlopen(f"{ollama_host()}/api/tags", timeout=5) as resp:
                tags = json.loads(resp.read())
                info["installed_models"] = [m["name"] for m in tags.get("models", [])]
        except Exception:
            info["installed_models"] = []
    return info
