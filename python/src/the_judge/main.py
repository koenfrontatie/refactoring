import asyncio
from the_judge.container import build_runtime          

async def main() -> None:
    rt = build_runtime()       
    
    
    await rt.ws_client.connect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
