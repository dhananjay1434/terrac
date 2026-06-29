import os
import sys
from pathlib import Path

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
