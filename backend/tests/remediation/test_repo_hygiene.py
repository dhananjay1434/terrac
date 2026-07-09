import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

# The demo secrets that were exposed before P0.3 (in demo_tools bats, a URL, and
# a prompt doc). They are now rotated/dead; they must never reappear committed.
_BURNED_SECRETS = (
    "demo-admin-secret-0123456789abcdefghij",
    "ZjOJkiNbTwQseznRNQT5zJwOXCin3N7pav3V9EGsr9s",
)


def _committed_text_files(subdir: str):
    """Yield (path, text) for text files under subdir, skipping the gitignored
    real-secrets file which legitimately holds live values."""
    base = _REPO_ROOT / subdir
    if not base.exists():
        return
    for p in base.rglob("*"):
        if not p.is_file() or p.name == "demo_secrets.bat":
            continue
        if p.suffix.lower() not in {".md", ".bat", ".py", ".html", ".txt", ".ps1", ".sh"}:
            continue
        try:
            yield p, p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue


def test_gitignore_blocks_signing_material_and_demo_secrets():
    content = (_REPO_ROOT / ".gitignore").read_text()
    assert "demo_secrets.bat" in content
    assert "*.jks" in content
    assert "key.properties" in content


def test_no_literal_secret_in_committed_demo_tools():
    # A committed demo file may reference secrets (%VAR%, sourcing) or show a
    # CHANGE_ME placeholder, but must never hardcode a real secret value.
    pat = re.compile(r"DMRV_(?:ADMIN|HMAC)_SECRET\s*=\s*([^\s%]{16,})")
    for p, text in _committed_text_files("demo_tools"):
        for m in pat.finditer(text):
            val = m.group(1)
            assert val.startswith("CHANGE_ME"), (
                f"{p.name}: hardcoded secret-looking value '{val[:8]}...' "
                f"in a committed demo file — load it from demo_secrets.bat instead"
            )


def test_burned_demo_secrets_absent_everywhere():
    for subdir in ("demo_tools", "docs"):
        for p, text in _committed_text_files(subdir):
            for burned in _BURNED_SECRETS:
                assert burned not in text, f"{p}: contains a burned demo secret"


def test_gitignore_ignores_env():
    repo_root = Path(__file__).parent.parent.parent.parent
    gitignore_path = repo_root / ".gitignore"
    content = gitignore_path.read_text()
    assert "backend/.env" in content or ".env" in content


def test_gitignore_ignores_db_and_build():
    repo_root = Path(__file__).parent.parent.parent.parent
    gitignore_path = repo_root / ".gitignore"
    content = gitignore_path.read_text()
    assert "*.db" in content
    assert "build/" in content


def test_no_prompt_dumps_present():
    repo_root = Path(__file__).parent.parent.parent.parent
    assert not (repo_root / "all_user_inputs.txt").exists()
    assert not (repo_root / "longest_msg.txt").exists()
    assert not (repo_root / "p0_12_block.txt").exists()


def test_no_throwaway_scripts():
    repo_root = Path(__file__).parent.parent.parent.parent
    scripts = list(repo_root.glob("*.py"))
    names = [s.name for s in scripts]
    assert "fix.py" not in names
    assert "find_p0_12.py" not in names
    assert "check_prompt.py" not in names


def test_env_example_documents_required_vars():
    backend_dir = Path(__file__).parent.parent.parent
    env_example = backend_dir / ".env.example"
    content = env_example.read_text()
    assert "DATABASE_URL" in content
    assert "DMRV_HMAC_SECRET" in content
    assert "DMRV_ALLOWED_ORIGIN" in content
    assert "MONGO_URL" not in content
    assert "CORS_ORIGINS" not in content


def test_cors_never_star_with_credentials():
    backend_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))

    os.environ["DMRV_HMAC_SECRET"] = "dummy"
    import server

    # In FastAPI, user_middleware holds the added middlewares
    from fastapi.middleware.cors import CORSMiddleware

    for middleware in server.app.user_middleware:
        if middleware.cls == CORSMiddleware:
            allow_origins = middleware.kwargs.get("allow_origins", [])
            allow_credentials = middleware.kwargs.get("allow_credentials", False)
            if allow_credentials:
                assert "*" not in allow_origins
