#!/bin/bash
set -e

echo "Waiting for MySQL..."
until python -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        return False
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        return True
    except Exception:
        return False
    finally:
        await engine.dispose()

import sys
sys.exit(0 if asyncio.run(check()) else 1)
" 2>/dev/null; do
    sleep 2
done

echo "MySQL is ready. Starting application..."
exec "$@"