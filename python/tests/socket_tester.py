#the-judge-app/socket_tester.py
"""
Generic Socket.IO Tester for The Judge
Connects to the socket server and sends events with optional payloads.
"""

import asyncio
import socketio
import argparse
import json
import sys
import socket
import time
from datetime import datetime

class SocketTester:
    def __init__(self, server_ip=None, server_port=8081):
        self.server_ip = server_ip or self._find_server_ip()
        self.server_port = server_port
        self.server_url = f"http://{self.server_ip}:{self.server_port}"
        
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.is_connected = False
        self.events_received = []
        self.waiting_for_response = False
        
        self._setup_handlers()
        
    def _find_server_ip(self):
        """Find server by hostname or return localhost."""
        try:
            return socket.gethostbyname('KVDWPC')
        except socket.gaierror:
            return "localhost"
            
    def _setup_handlers(self):
        """Setup Socket.IO event handlers to capture all responses."""
        
        @self.sio.event
        async def connect():
            self.is_connected = True
            print(f"[CONNECTED] {self.server_url}")
            
        @self.sio.event
        async def disconnect():
            self.is_connected = False
            print(f"[DISCONNECTED] {self.server_url}")
            
        @self.sio.event
        async def connect_error(error):
            print(f"[ERROR] Connection failed: {error}")
            
        # Capture ALL incoming events
        @self.sio.event
        async def __catch_all(event_name, *args):
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.events_received.append((event_name, args, timestamp))
            print(f"[{timestamp}] RECEIVED: {event_name}")
            if args:
                for i, arg in enumerate(args):
                    if isinstance(arg, dict) or isinstance(arg, list):
                        print(f"    payload[{i}]: {json.dumps(arg, indent=2)}")
                    else:
                        print(f"    payload[{i}]: {arg}")
            print()
            
        # Override the catch-all for specific events we want to handle
        self.sio._callbacks = {}
        self.sio.on('*', __catch_all)
        
    async def connect(self):
        """Connect to the socket server."""
        try:
            print(f"[CONNECTING] {self.server_url}...")
            await self.sio.connect(self.server_url)
            
            # Register as a test client
            await self.sio.emit('register', {'clientType': 'test'})
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            return False
            
    async def send_event(self, event_name, payload=None, wait_time=2):
        """Send an event and wait for responses."""
        if not self.is_connected:
            print("[ERROR] Not connected to server")
            return False
            
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] SENDING: {event_name}")
            
            if payload:
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        # If it's not JSON, treat it as a simple string
                        pass
                        
                print(f"    payload: {json.dumps(payload, indent=2) if isinstance(payload, (dict, list)) else payload}")
            
            print()
            
            # Clear previous events
            initial_event_count = len(self.events_received)
            
            # Send the event
            await self.sio.emit(event_name, payload)
            
            # Wait for responses
            print(f"[WAITING] {wait_time}s for responses...")
            await asyncio.sleep(wait_time)
            
            # Show summary
            new_events = len(self.events_received) - initial_event_count
            if new_events > 0:
                print(f"[SUMMARY] Received {new_events} response(s)")
            else:
                print(f"[SUMMARY] No responses received")
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to send event: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from server."""
        if self.is_connected:
            await self.sio.disconnect()
            
    def show_event_history(self):
        """Show all received events."""
        if not self.events_received:
            print("[INFO] No events received yet")
            return
            
        print(f"\n[EVENT HISTORY] {len(self.events_received)} events received:")
        print("-" * 60)
        
        for event_name, args, timestamp in self.events_received:
            print(f"[{timestamp}] {event_name}")
            if args:
                for i, arg in enumerate(args):
                    if isinstance(arg, (dict, list)):
                        print(f"    {json.dumps(arg, indent=4)}")
                    else:
                        print(f"    {arg}")
            print()

async def main():
    parser = argparse.ArgumentParser(
        description='Generic Socket.IO Tester for The Judge',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple command names
  python socket_tester.py camera_manager_capture
  python socket_tester.py camera_manager_toggle
  python socket_tester.py camera_manager_status
  
  # Multiple commands
  python socket_tester.py camera_manager_status camera_manager_capture
  
  # With payload (legacy)
  python socket_tester.py --event camera_manager_capture --payload '{"test": true}'
  
  # Interactive mode
  python socket_tester.py --interactive
        """
    )
    
    parser.add_argument('commands', nargs='*', help='Command name(s) to send')
    parser.add_argument('--server-ip', '-s', help='Server IP address (auto-detect if not specified)')
    parser.add_argument('--server-port', '-p', type=int, default=8081, help='Server port (default: 8081)')
    parser.add_argument('--event', '-e', action='append', help='Event name to send (can specify multiple)')
    parser.add_argument('--payload', help='JSON payload to send with event')
    parser.add_argument('--wait', '-w', type=float, default=2.0, help='Seconds to wait for responses (default: 2)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--list-events', '-l', action='store_true', help='List common event names')
    
    args = parser.parse_args()
    
    if args.list_events:
        print("Common Camera Manager Events:")
        print("  camera_manager_status")
        print("  camera_manager_toggle") 
        print("  camera_manager_capture")
        print("  camera_manager_remote_register")
        print("  camera_manager_remote_unregister")
        print("\nOther System Events:")
        print("  webcam_control")
        print("  content_control")
        print("  process")
        print("  batch_process")
        return
    
    # Create tester
    tester = SocketTester(args.server_ip, args.server_port)
    
    try:
        # Connect
        if not await tester.connect():
            return 1
            
        if args.interactive:
            # Interactive mode
            print("\n[INTERACTIVE MODE]")
            print("Commands:")
            print("  send <event_name> [payload]  - Send an event")
            print("  <event_name>                 - Send event without payload")
            print("  history                      - Show event history")  
            print("  clear                        - Clear event history")
            print("  quit                         - Exit")
            print()
            
            while True:
                try:
                    cmd = input("socket_tester> ").strip()
                    
                    if not cmd:
                        continue
                        
                    if cmd == 'quit':
                        break
                    elif cmd == 'history':
                        tester.show_event_history()
                    elif cmd == 'clear':
                        tester.events_received.clear()
                        print("[INFO] Event history cleared")
                    elif cmd.startswith('send '):
                        parts = cmd.split(' ', 2)
                        event_name = parts[1]
                        payload = parts[2] if len(parts) > 2 else None
                        await tester.send_event(event_name, payload, args.wait)
                    else:
                        # Treat as direct event name
                        await tester.send_event(cmd, None, args.wait)
                        
                except KeyboardInterrupt:
                    break
                except EOFError:
                    break
                    
        elif args.commands:
            # Send commands by name
            for cmd in args.commands:
                await tester.send_event(cmd, None, args.wait)
                
        elif args.event:
            # Legacy --event mode
            for event_name in args.event:
                await tester.send_event(event_name, args.payload, args.wait)
                
        else:
            # Send specified events
            print("[ERROR] No commands specified. Use command names, --event, or --interactive")
            return 1
                
        return 0
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        return 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
