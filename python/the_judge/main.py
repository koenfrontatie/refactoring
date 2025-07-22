import asyncio

from the_judge.common.logger import setup_logger
from the_judge.container import create_app

logger = setup_logger("main")

async def main() -> None:
    app = create_app()
    try:
        await app.start()
    except KeyboardInterrupt:
        pass
    finally:
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())

