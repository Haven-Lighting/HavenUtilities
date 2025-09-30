import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import datetime
import time
import os

class SerialTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Terminal")
        self.root.geometry("700x600")
        self.root.minsize(400, 300)
        self.ser = None
        self.connected = False
        self.no_ports_label = None
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Playlist Builder", command=self.open_playlist_builder)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save to File", command=self.save_to_file)
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Selection frame
        sel_frame = ttk.Frame(self.root)
        sel_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Port
        ttk.Label(sel_frame, text="COM Port:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(sel_frame, textvariable=self.port_var, width=20)
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(sel_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(sel_frame, text="Save File", command=self.save_to_downloads).grid(row=0, column=3, padx=5, pady=5)
        self.refresh_ports()
        
        # Baud
        ttk.Label(sel_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.baud_var = tk.StringVar(value="460800")
        baud_combo = ttk.Combobox(sel_frame, textvariable=self.baud_var, 
                                  values=["9600", "19200", "38400", "57600", "115200", "250000", "460800", "500000", "1000000"], 
                                  width=20)
        baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Connect button
        self.connect_btn = ttk.Button(sel_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=2, column=0, columnspan=4, pady=10)
        
        # Playlist button
        ttk.Button(sel_frame, text="Open Playlist Creator Window", command=self.open_playlist_builder).grid(row=3, column=0, columnspan=4, pady=5)
        
        self.update_no_ports_label(sel_frame)
        
        # Terminal frame
        self.terminal_frame = ttk.Frame(self.root)
        self.terminal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.terminal = scrolledtext.ScrolledText(self.terminal_frame, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9))
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        # Command frame
        self.cmd_frame = ttk.Frame(self.root)
        self.cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cmd_entry = ttk.Entry(self.cmd_frame)
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", self.send_cmd)
        
        ttk.Button(self.cmd_frame, text="Send", command=self.send_cmd).pack(side=tk.RIGHT, padx=(5,0))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        sel_frame.columnconfigure(1, weight=1)
        self.cmd_frame.columnconfigure(0, weight=1)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.cmd_entry.focus_set()
    
    def save_to_file(self):
        self.terminal.config(state=tk.NORMAL)
        content = self.terminal.get("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, 'w') as f:
                f.write(content)
            messagebox.showinfo("Saved", "Terminal content saved.")
    
    def save_to_downloads(self):
        self.terminal.config(state=tk.NORMAL)
        content = self.terminal.get("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloads, f"terminal_log_{timestamp}.txt")
        with open(filename, 'w') as f:
            f.write(content)
        self.log(f"Saved to {filename}")
    
    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_var.set(ports[0])
        self.update_no_ports_label(self.root.winfo_children()[0])
    
    def update_no_ports_label(self, parent):
        if self.no_ports_label:
            self.no_ports_label.destroy()
        ports = self.port_combo['values']
        if not ports:
            self.no_ports_label = ttk.Label(parent, text="No ports detected.", foreground="red")
            self.no_ports_label.grid(row=4, column=0, columnspan=4, pady=5)
    
    def toggle_connection(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        if not self.port_var.get():
            messagebox.showwarning("Warning", "Select a COM port.")
            return
        try:
            self.ser = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
            self.connected = True
            self.connect_btn.config(text="Disconnect")
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.log(f"Connected: {self.port_var.get()} @ {self.baud_var.get()}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def disconnect(self):
        if self.connected:
            self.ser.close()
            self.connected = False
            self.connect_btn.config(text="Connect")
            self.log("Disconnected")
    
    def on_closing(self):
        if self.connected:
            self.disconnect()
        self.root.quit()
    
    def read_serial(self):
        while self.connected:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if data:
                        self.log(f"RX: {data}")
            except Exception as e:
                self.log(f"Read error: {e}")
                break
        self.connected = False
    
    def send_cmd(self, event=None):
        if self.connected:
            cmd = self.cmd_entry.get().strip()
            if cmd:
                self.send_raw(cmd)
                self.cmd_entry.delete(0, tk.END)
    
    def send_raw(self, cmd):
        if self.connected:
            try:
                self.ser.write((cmd + "\r\n").encode())
                self.log(f"TX: {cmd}")
            except Exception as e:
                self.log(f"TX Error: {e}")
    
    def log(self, msg):
        self.terminal.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
    
    def open_playlist_builder(self):
        self.playlist_window = tk.Toplevel(self.root)
        self.playlist_window.title("Playlist Builder")
        self.playlist_window.geometry("500x400")
        
        frame = ttk.Frame(self.playlist_window)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Playlist ID
        ttk.Label(frame, text="Playlist ID:").grid(row=0, column=0, sticky="w")
        self.pl_id_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=self.pl_id_var, width=10).grid(row=0, column=1, sticky="w")
        
        # Add action frame
        add_frame = ttk.Frame(frame)
        add_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(add_frame, text="Action ID:").pack(side=tk.LEFT)
        self.action_var = tk.StringVar()
        action_combo = ttk.Combobox(add_frame, textvariable=self.action_var, values=list(range(10)), width=5)
        action_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(add_frame, text="Duration (ms):").pack(side=tk.LEFT)
        self.dur_var = tk.StringVar(value="5000")
        ttk.Entry(add_frame, textvariable=self.dur_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="Add", command=self.add_action).pack(side=tk.LEFT)
        
        # Treeview for actions
        columns = ("Action ID", "Duration")
        self.action_tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        self.action_tree.heading("Action ID", text="Action ID")
        self.action_tree.heading("Duration", text="Duration")
        self.action_tree.column("Action ID", width=80)
        self.action_tree.column("Duration", width=100)
        self.action_tree.grid(row=3, column=0, columnspan=3, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.action_tree.yview)
        self.action_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=3, column=3, sticky="ns")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Create Playlist", command=self.create_playlist).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Play Playlist", command=self.play_playlist).pack(side=tk.LEFT, padx=5)
        
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)
    
    def add_action(self):
        act_id = self.action_var.get()
        dur = self.dur_var.get()
        if act_id and dur:
            self.action_tree.insert("", "end", values=(act_id, dur))
    
    def get_actions(self):
        actions = []
        for item in self.action_tree.get_children():
            vals = self.action_tree.item(item)['values']
            actions.append((vals[0], vals[1]))
        return actions
    
    def create_playlist(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        pl_id = self.pl_id_var.get()
        actions = self.get_actions()
        if not actions:
            messagebox.showwarning("Warning", "No actions added.")
            return
        # Create table
        create_cmd = 'CREATE TABLE IF NOT EXISTS Playlist_table (id INTEGER PRIMARY KEY AUTOINCREMENT, playlist_id INTEGER, action_id INTEGER, duration INTEGER);'
        self.send_raw(create_cmd)
        # Inserts
        for act_id, dur in actions:
            insert_cmd = f'INSERT INTO Playlist_table (playlist_id, action_id, duration) VALUES ({pl_id}, {act_id}, {dur});'
            self.send_raw(insert_cmd)
        self.log("Playlist created and sent to controller.")
    
    def play_playlist(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        pl_id = self.pl_id_var.get()
        epoch = int(time.time() * 1000)
        cmd = f'LIGHTING.ON({{"CH":[1],"Function":"executePlaylist","Config":{{"playList_ID":{pl_id},"epocStartTime":{epoch},"durationMsec":0,"termination":-1}}}})'
        self.send_raw(cmd)
        self.log("Playlist execution command sent (infinite loop).")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTerminal(root)
    root.mainloop()