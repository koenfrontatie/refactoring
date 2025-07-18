import asyncio
from container import build_runtime          
from common import logger

logger.setup_logger("main")

async def main() -> None:
    app = build_runtime()       
    
    try:
        await app.ws_client.connect()
    except KeyboardInterrupt:
            # allow Ctrl‑C to break us out
            pass
    finally:
        try:
            await app.ws_client.disconnect()
        except Exception:
            pass
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
