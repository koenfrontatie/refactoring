import asyncio
from container import build_runtime          

async def main() -> None:
    rt = build_runtime()       
    
    try:
        await rt.ws_client.connect()
    except KeyboardInterrupt:
            # allow Ctrl‑C to break us out
            pass
    finally:
        try:
            await rt.ws_client.disconnect()
        except Exception:
            pass
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
