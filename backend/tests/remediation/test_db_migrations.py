import os
import pytest
import pytest_asyncio
from unittest.mock import patch

pytestmark = pytest.mark.asyncio

async def test_migrations_gated():
    from db import init_db
    
    # Set the flag to 1
    os.environ["DMRV_SKIP_MIGRATIONS"] = "1"
    
    with patch("alembic.command.upgrade") as mock_upgrade:
        await init_db()
        mock_upgrade.assert_not_called()
        
    # Set the flag to 0
    os.environ["DMRV_SKIP_MIGRATIONS"] = "0"
    
    with patch("alembic.command.upgrade") as mock_upgrade:
        # Catch the exception because the fake DB_URL might fail in asyncio.to_thread
        # Or mock asyncio.to_thread
        pass
    
    with patch("asyncio.to_thread") as mock_thread:
        await init_db()
        mock_thread.assert_called_once()
