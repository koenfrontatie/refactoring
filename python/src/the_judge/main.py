import asyncio
from the_judge.common.logger import setup_logger
from the_judge.container import build_runtime          

logger = setup_logger("Main")

async def main() -> None:
    rt = build_runtime()       
    ws_client = rt.ws_client

    logger.info("The Judge started.")
    await ws_client.connect()  # blocks until Ctrl‑C

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown")
