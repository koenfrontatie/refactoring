#!/usr/bin/env python3
import asyncio
import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socketio
from datetime import datetime

# Add the parent directory to the path so we can import from the_judge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from the_judge.settings import get_settings


class SocketTestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Socket Test GUI")
        self.root.geometry("600x500")
        
        self.settings = get_settings()
        self.sio = socketio.AsyncClient(reconnection=True)
        self.connected = False
        
        # Setup socket events exactly like CLI
        @self.sio.event
        async def connect():
            print("Connected to server")
            self.connected = True
            await self.sio.emit('register', {'clientType': 'test_gui'})
            self.log("Connected and registered")
            self.update_ui()
            
        @self.sio.event
        async def disconnect():
            print("Disconnected from server")
            self.connected = False
            self.log("Disconnected")
            self.update_ui()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Connection frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding="10")
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        # Server URL
        ttk.Label(conn_frame, text="Server URL:").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar(value=self.settings.socket_url)
        url_entry = ttk.Entry(conn_frame, textvariable=self.url_var, width=40)
        url_entry.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Connection status and button
        self.status_var = tk.StringVar(value="Disconnected")
        ttk.Label(conn_frame, text="Status:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.status_label = ttk.Label(conn_frame, textvariable=self.status_var, foreground="red")
        self.status_label.grid(row=1, column=1, sticky="w", padx=(5, 0), pady=(5, 0))
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        conn_frame.columnconfigure(1, weight=1)
        
        # Commands frame
        cmd_frame = ttk.LabelFrame(self.root, text="Commands", padding="10")
        cmd_frame.pack(fill="x", padx=10, pady=5)
        
        # Trigger button
        self.trigger_btn = ttk.Button(cmd_frame, text="Trigger Collection", 
                                     command=self.send_trigger, state="disabled")
        self.trigger_btn.pack(pady=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(self.root, text="Log", padding="10")
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=(5, 0))
    
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
    
    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
    
    def update_ui(self):
        if self.connected:
            self.status_var.set("Connected")
            self.status_label.config(foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.trigger_btn.config(state="normal")
        else:
            self.status_var.set("Disconnected")
            self.status_label.config(foreground="red")
            self.connect_btn.config(text="Connect")
            self.trigger_btn.config(state="disabled")
    
    def toggle_connection(self):
        if self.connected:
            asyncio.create_task(self.disconnect())
        else:
            asyncio.create_task(self.connect())
    
    async def connect(self):
        uri = self.url_var.get().replace("ws://", "http://").replace("wss://", "https://")
        try:
            await self.sio.connect(uri)
            await asyncio.sleep(1)  # Wait for registration
        except Exception as e:
            self.log(f"Failed to connect: {e}")
    
    async def disconnect(self):
        if self.sio.connected:
            await self.sio.disconnect()
    
    def send_trigger(self):
        if self.connected:
            asyncio.create_task(self.async_send_trigger())
        else:
            messagebox.showwarning("Not Connected", "Please connect to server first!")
    
    async def async_send_trigger(self):
        try:
            await self.sio.emit('camera.trigger_collection', {})
            self.log("Sent trigger collection command")
        except Exception as e:
            self.log(f"Error sending trigger: {e}")


async def main():
    root = tk.Tk()
    app = SocketTestGUI(root)
    
    def update_gui():
        root.update()
        asyncio.get_event_loop().call_later(0.01, update_gui)
    
    update_gui()
    
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if app.connected:
            await app.disconnect()
        root.destroy()


if __name__ == '__main__':
    asyncio.run(main())
