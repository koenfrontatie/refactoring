#!/usr/bin/env python3
import asyncio
import sys
import os
import socketio

# Add the parent directory to the path so we can import from the_judge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from the_judge.settings import get_settings

class SocketTestCLI:
    def __init__(self):
        self.settings = get_settings()
        self.sio = socketio.AsyncClient(reconnection=True)
        self.connected = False
        
        @self.sio.event
        async def connect():
            print("Connected to server")
            self.connected = True
            await self.sio.emit('register', {'clientType': 'test_cli'})
            
        @self.sio.event
        async def disconnect():
            print("Disconnected from server")
            self.connected = False
            
    async def connect_to_server(self):
        uri = self.settings.socket_url.replace("ws://", "http://").replace("wss://", "https://")
        try:
            await self.sio.connect(uri)
            print(f"Connected to {uri}")
            await asyncio.sleep(1)  # Wait for registration
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
            
    async def send_trigger(self):
        if not self.connected:
            print("Not connected!")
            return
        await self.sio.emit('camera.trigger_collection', {})
        print("Sent trigger event")
        
    async def run(self):
        if not await self.connect_to_server():
            return
            
        print("CLI connected. Commands:")
        print("  't' - trigger collection")
        print("  'q' - quit")
        
        # Use asyncio to handle input without blocking
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            while True:
                try:
                    # Run input in a separate thread to avoid blocking
                    future = executor.submit(input, "Enter command: ")
                    
                    # Wait for input with a timeout to allow other async operations
                    while not future.done():
                        await asyncio.sleep(0.1)
                    
                    cmd = future.result().strip().lower()
                    
                    if cmd == 'q':
                        break
                    elif cmd == 't':
                        await self.send_trigger()
                    else:
                        print("Unknown command")
                        
                except (KeyboardInterrupt, EOFError):
                    break
                    
        await self.sio.disconnect()
        print("Goodbye!")

async def main():
    cli = SocketTestCLI()
    await cli.run()

if __name__ == '__main__':
    asyncio.run(main())
