import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from datetime import datetime
import socket
import threading
import struct
import os
import queue
import binascii
import random
import time

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.on_enter)
        self.widget.bind("<Leave>", self.on_leave)
    
    def on_enter(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, background="#ffffe0", 
                        relief='solid', borderwidth=1, font=("Arial", 9), 
                        wraplength=300, justify='left', padx=5, pady=3)
        label.pack()
    
    def on_leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class UDPWritePopup:
    def __init__(self, parent):
        self.parent = parent
        self.popup = tk.Toplevel(parent.root)
        self.popup.title("UDP Write")
        self.popup.geometry("300x200")
        self.popup.configure(bg='black')
        
        tk.Label(self.popup, text="Target IP:", fg='white', bg='black').pack(pady=5)
        self.target_ip = tk.Entry(self.popup, bg='#404040', fg='white', insertbackground='white')
        self.target_ip.pack(pady=5)
        self.target_ip.insert(0, "127.0.0.1")
        
        tk.Label(self.popup, text="Target Port:", fg='white', bg='black').pack(pady=5)
        self.target_port = tk.Entry(self.popup, bg='#404040', fg='white', insertbackground='white')
        self.target_port.pack(pady=5)
        self.target_port.insert(0, "6682")
        
        tk.Label(self.popup, text="Message:", fg='white', bg='black').pack(pady=5)
        self.message_entry = tk.Text(self.popup, height=4, bg='black', fg='white', insertbackground='white', font=('Arial', 12))
        self.message_entry.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        button_frame = tk.Frame(self.popup, bg='black')
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Send", command=self.send_udp, bg='#404040', fg='black', relief='flat').pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=self.popup.destroy, bg='#404040', fg='black', relief='flat').pack(side=tk.LEFT, padx=5)
    
    def send_udp(self):
        ip = self.target_ip.get()
        port = int(self.target_port.get())
        message = self.message_entry.get("1.0", tk.END).strip().encode()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message, (ip, port))
            sock.close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

class TFTPUDPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TFTP & UDP Utility")
        self.root.geometry("800x600")
        self.root.configure(bg='black')
        
        self.sending = False
        self.abort_flag = False
        self.tftp_sock = None
        self.tftp_msg_queue = queue.Queue()
        self.tftp_mode = "send"  # "send" or "listen"
        self.tftp_listening = False
        self.tftp_listen_thread = None
        self._stop_sending_flag = False
        
        # Top half: TFTP Panel
        self.tftp_frame = tk.Frame(root, height=300, bg='#2c2c2c')
        self.tftp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        tk.Label(self.tftp_frame, text="TFTP", font=('Arial', 16), fg='white', bg='#2c2c2c').pack(pady=10)
        
        # Mode toggle frame
        mode_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        mode_frame.pack(pady=5)
        tk.Label(mode_frame, text="Mode:", fg='white', bg='#2c2c2c').pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value="send")
        self.send_radio = tk.Radiobutton(mode_frame, text="Send", variable=self.mode_var, value="send", 
                                         command=self.switch_mode, bg='#2c2c2c', fg='white', 
                                         selectcolor='#404040', activebackground='#2c2c2c')
        self.send_radio.pack(side=tk.LEFT, padx=5)
        self.listen_radio = tk.Radiobutton(mode_frame, text="Listen", variable=self.mode_var, value="listen", 
                                           command=self.switch_mode, bg='#2c2c2c', fg='white', 
                                           selectcolor='#404040', activebackground='#2c2c2c')
        self.listen_radio.pack(side=tk.LEFT, padx=5)
        
        # IP address frame
        ip_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        ip_frame.pack(pady=5)
        self.ip_label = tk.Label(ip_frame, text="Target IP:", fg='white', bg='#2c2c2c')
        self.ip_label.pack(side=tk.LEFT)
        
        # IP Entry (for Send mode)
        self.ip_entry = tk.Entry(ip_frame, width=20, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "10.10.2.46")
        
        # IP Display Label (for Listen mode - initially hidden)
        self.ip_display = tk.Label(ip_frame, text="", fg='white', bg='#2c2c2c', font=('Arial', 12), width=20, anchor='w')
        # Don't pack it yet - will be shown in listen mode
        
        # Send mode controls
        self.send_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        self.send_frame.pack(pady=5)
        
        file_frame = tk.Frame(self.send_frame, bg='#2c2c2c')
        file_frame.pack(pady=5)
        tk.Label(file_frame, text="File:", fg='white', bg='#2c2c2c').pack(side=tk.LEFT)
        self.file_entry = tk.Entry(file_frame, width=40, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.file_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="Browse", command=self.browse_file, bg='#404040', fg='black', relief='flat').pack(side=tk.LEFT, padx=5)
        
        # Send header
        tk.Label(self.send_frame, text="Send", fg='white', bg='#2c2c2c', font=('Arial', 10, 'bold')).pack(pady=(10, 2))
        
        btn_frame = tk.Frame(self.send_frame, bg='#2c2c2c')
        btn_frame.pack(pady=5)
        self.normal_send_btn = tk.Button(btn_frame, text="TFTP Send", command=self.normal_send_tftp, bg='#00aa00', fg='white', relief='flat')
        self.normal_send_btn.pack(side=tk.LEFT, padx=5)
        
        # Failure simulation buttons - First row
        tk.Label(self.send_frame, text="Failure Simulations:", fg='#888888', bg='#2c2c2c', font=('Arial', 9)).pack(pady=(10, 2))
        
        btn_frame2 = tk.Frame(self.send_frame, bg='#2c2c2c')
        btn_frame2.pack(pady=2)
        self.fail_outoforder_btn = tk.Button(btn_frame2, text="Out-of-Order", command=self.failure_out_of_order, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_outoforder_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_outoforder_btn, "Sends blocks 1,2,4,3,5,6... to test handling of misordered packets")
        
        self.fail_duplicate_btn = tk.Button(btn_frame2, text="Duplicates", command=self.failure_duplicate, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_duplicate_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_duplicate_btn, "Sends some blocks twice to test duplicate detection")
        
        self.fail_wrongnum_btn = tk.Button(btn_frame2, text="Wrong Block #", command=self.failure_wrong_numbers, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_wrongnum_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_wrongnum_btn, "Uses incorrect block numbering to test validation")
        
        # Failure simulation buttons - Second row
        btn_frame3 = tk.Frame(self.send_frame, bg='#2c2c2c')
        btn_frame3.pack(pady=2)
        self.fail_truncated_btn = tk.Button(btn_frame3, text="Truncated", command=self.failure_truncated, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_truncated_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_truncated_btn, "Stops after sending 60% of file to test incomplete transfers")
        
        self.fail_timeout_btn = tk.Button(btn_frame3, text="Timeout", command=self.failure_timeout, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_timeout_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_timeout_btn, "Pauses 10 seconds mid-transfer to test timeout handling")
        
        self.fail_pktloss_btn = tk.Button(btn_frame3, text="Packet Loss", command=self.failure_packet_loss, bg='#ff0000', fg='white', relief='flat', width=12)
        self.fail_pktloss_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.fail_pktloss_btn, "Randomly drops ~30% of packets to test loss detection")
        
        self.swap_send_btn = tk.Button(btn_frame3, text="Data Swap", command=self.swap_send_tftp, bg='#ff0000', fg='white', relief='flat', width=12)
        self.swap_send_btn.pack(side=tk.LEFT, padx=3)
        self.create_tooltip(self.swap_send_btn, "Swaps two random bytes in file data to test data corruption detection")
        
        # Listen mode controls
        self.listen_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        
        output_frame = tk.Frame(self.listen_frame, bg='#2c2c2c')
        output_frame.pack(pady=5)
        tk.Label(output_frame, text="Output File:", fg='white', bg='#2c2c2c').pack(side=tk.LEFT)
        self.output_entry = tk.Entry(output_frame, width=40, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.output_entry.pack(side=tk.LEFT, padx=5)
        self.output_entry.insert(0, "received.bin")
        
        listen_btn_frame = tk.Frame(self.listen_frame, bg='#2c2c2c')
        listen_btn_frame.pack(pady=10)
        self.start_listen_btn = tk.Button(listen_btn_frame, text="Start Listen", command=self.toggle_listen, bg='#1a1a1a', fg='white', relief='flat')
        self.start_listen_btn.pack(side=tk.LEFT, padx=5)
        
        # Abort button frame and progress, initially not packed
        self.abort_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        self.abort_btn = tk.Button(self.abort_frame, text="Abort Send", command=self.abort_send, bg='#ff0000', fg='white', relief='flat')
        self.abort_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(self.tftp_frame, mode='indeterminate', length=200)
        
        # TFTP text area with both vertical and horizontal scrollbars
        self.tftp_text_frame = tk.Frame(self.tftp_frame, bg='black')
        self.tftp_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create scrollbars
        tftp_vscroll = tk.Scrollbar(self.tftp_text_frame, orient='vertical')
        tftp_hscroll = tk.Scrollbar(self.tftp_text_frame, orient='horizontal')
        
        # Create text widget
        self.tftp_text = tk.Text(self.tftp_text_frame, height=8, state='disabled', bg='black', fg='white', 
                                 insertbackground='white', font=('Courier', 10), wrap='none',
                                 yscrollcommand=tftp_vscroll.set, xscrollcommand=tftp_hscroll.set)
        
        # Configure scrollbars
        tftp_vscroll.config(command=self.tftp_text.yview)
        tftp_hscroll.config(command=self.tftp_text.xview)
        
        # Grid layout for text and scrollbars
        self.tftp_text.grid(row=0, column=0, sticky='nsew')
        tftp_vscroll.grid(row=0, column=1, sticky='ns')
        tftp_hscroll.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        self.tftp_text_frame.grid_rowconfigure(0, weight=1)
        self.tftp_text_frame.grid_columnconfigure(0, weight=1)
        
        self.poll_tftp_queue()
        
        # Initialize to send mode
        self.switch_mode()
        
        # Bottom half: UDP Terminal
        self.udp_frame = tk.Frame(root, height=300, bg='#1a1a1a')
        self.udp_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        tk.Label(self.udp_frame, text="UDP Terminal", font=('Arial', 16), fg='white', bg='#1a1a1a').pack(pady=10)
        
        port_frame = tk.Frame(self.udp_frame, bg='#1a1a1a')
        port_frame.pack(pady=5)
        tk.Label(port_frame, text="Port:", fg='white', bg='#1a1a1a').pack(side=tk.LEFT)
        self.port_entry = tk.Entry(port_frame, width=10, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.port_entry.pack(side=tk.LEFT, padx=5)
        self.port_entry.insert(0, "6682")
        
        self.open_btn = tk.Button(port_frame, text="UDP Open", command=self.toggle_udp, bg='#404040', fg='black', relief='flat')
        self.open_btn.pack(side=tk.LEFT, padx=5)
        
        self.write_btn = tk.Button(port_frame, text="UDP Write", command=self.open_write_popup, bg='#404040', fg='black', relief='flat')
        self.write_btn.pack(side=tk.LEFT, padx=5)
        
        # UDP text area with both vertical and horizontal scrollbars
        udp_text_frame = tk.Frame(self.udp_frame, bg='black')
        udp_text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create scrollbars
        udp_vscroll = tk.Scrollbar(udp_text_frame, orient='vertical')
        udp_hscroll = tk.Scrollbar(udp_text_frame, orient='horizontal')
        
        # Create text widget
        self.udp_text = tk.Text(udp_text_frame, height=15, state='disabled', bg='black', fg='white', 
                                insertbackground='white', font=('Courier', 10), wrap='none',
                                yscrollcommand=udp_vscroll.set, xscrollcommand=udp_hscroll.set)
        
        # Configure scrollbars
        udp_vscroll.config(command=self.udp_text.yview)
        udp_hscroll.config(command=self.udp_text.xview)
        
        # Grid layout for text and scrollbars
        self.udp_text.grid(row=0, column=0, sticky='nsew')
        udp_vscroll.grid(row=0, column=1, sticky='ns')
        udp_hscroll.grid(row=1, column=0, sticky='ew')
        
        # Configure grid weights
        udp_text_frame.grid_rowconfigure(0, weight=1)
        udp_text_frame.grid_columnconfigure(0, weight=1)
        
        # UDP Socket
        self.udp_sock = None
        self.udp_thread = None
        self.udp_running = False
        self.msg_queue = queue.Queue()
        self.poll_queue()
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        ToolTip(widget, text)
    
    def poll_tftp_queue(self):
        try:
            while True:
                msg = self.tftp_msg_queue.get_nowait()
                self.tftp_text.config(state='normal')
                self.tftp_text.insert(tk.END, msg)
                self.tftp_text.config(state='disabled')
                self.tftp_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_tftp_queue)
        
        # Check if we need to stop sending
        if hasattr(self, '_stop_sending_flag') and self._stop_sending_flag:
            self._stop_sending_flag = False
            self.stop_sending()
    
    def get_local_ip(self):
        """Get the local IP address of this computer"""
        try:
            # Create a socket to get the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to a public DNS server (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def switch_mode(self):
        """Switch between Send and Listen modes"""
        mode = self.mode_var.get()
        self.tftp_mode = mode
        
        if mode == "send":
            # Show send controls, hide listen controls
            self.send_frame.pack(pady=5, before=self.tftp_text_frame)
            self.listen_frame.pack_forget()
            
            # Update IP label and show entry field, hide display label
            self.ip_label.config(text="Target IP:")
            self.ip_display.pack_forget()
            self.ip_entry.pack(side=tk.LEFT, padx=5)
            if self.ip_entry.get() == self.get_local_ip():
                self.ip_entry.delete(0, tk.END)
                self.ip_entry.insert(0, "10.10.2.46")
        else:  # listen mode
            # Show listen controls, hide send controls
            self.send_frame.pack_forget()
            self.listen_frame.pack(pady=5, before=self.tftp_text_frame)
            
            # Update IP label and show display label, hide entry field
            self.ip_label.config(text="Listen IP:")
            local_ip = self.get_local_ip()
            self.ip_entry.pack_forget()
            self.ip_display.config(text=local_ip)
            self.ip_display.pack(side=tk.LEFT, padx=5)
    
    def toggle_listen(self):
        """Start or stop TFTP listening"""
        if not self.tftp_listening:
            # Get IP from the display label (in listen mode)
            ip = self.ip_display.cget("text")
            filename = self.output_entry.get()
            try:
                self.tftp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.tftp_sock.bind((ip, 69))
                self.tftp_listening = True
                self.start_listen_btn.config(text="Stop Listen", bg='#ff0000')
                self.tftp_listen_thread = threading.Thread(target=self.tftp_server, args=(filename,), daemon=True)
                self.tftp_listen_thread.start()
                self.tftp_msg_queue.put(f"Listening for TFTP on {ip}:69\n")
                
                # Disable mode switching while listening
                self.send_radio.config(state='disabled')
                self.listen_radio.config(state='disabled')
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            self.tftp_listening = False
            if self.tftp_sock:
                self.tftp_sock.close()
                self.tftp_sock = None
            self.start_listen_btn.config(text="Start Listen", bg='#1a1a1a')
            self.tftp_msg_queue.put("Stopped listening\n")
            
            # Re-enable mode switching
            self.send_radio.config(state='normal')
            self.listen_radio.config(state='normal')
    
    def tftp_server(self, out_filename):
        """TFTP server for receiving files"""
        while self.tftp_listening:
            try:
                data, addr = self.tftp_sock.recvfrom(1024)
                opcode = struct.unpack('!H', data[:2])[0]
                if opcode == 2:  # WRQ
                    # Parse filename and mode
                    filename_end = data[2:].find(b'\0')
                    filename_req = data[2:2 + filename_end].decode()
                    mode_start = 2 + filename_end + 1
                    mode_end_rel = data[mode_start:].find(b'\0')
                    mode_end = mode_start + mode_end_rel
                    mode = data[mode_start:mode_end].decode()
                    
                    self.tftp_msg_queue.put(f"WRQ from {addr}: {filename_req} ({mode})\n")
                    
                    # Parse options
                    opt_data = data[mode_end + 1:]
                    expected_size = None
                    while len(opt_data) > 0:
                        key_end = opt_data.find(b'\0')
                        if key_end == -1:
                            break
                        key = opt_data[:key_end].decode()
                        opt_data = opt_data[key_end + 1:]
                        val_end = opt_data.find(b'\0')
                        if val_end == -1:
                            break
                        val = opt_data[:val_end].decode()
                        opt_data = opt_data[val_end + 1:]
                        if key == 'size':
                            expected_size = int(val)
                    
                    # Send OACK or ACK 0
                    if expected_size is not None:
                        oack = struct.pack('!H', 6) + b'size\0' + str(expected_size).encode() + b'\0'
                        self.tftp_sock.sendto(oack, addr)
                        self.tftp_msg_queue.put(f"Sent OACK with expected size {expected_size}\n")
                    else:
                        ack = struct.pack('!HH', 4, 0)
                        self.tftp_sock.sendto(ack, addr)
                    
                    # Open file and receive
                    total_received = 0
                    expected_blocks = []
                    received_blocks = []
                    missing_blocks = []
                    
                    with open(out_filename, 'wb') as f:
                        block_num = 1
                        consecutive_missing = 0
                        last_received_block = 0
                        
                        while self.tftp_listening:
                            try:
                                # Set a timeout for receiving packets
                                self.tftp_sock.settimeout(5.0)
                                data_pkt, addr_check = self.tftp_sock.recvfrom(1024)
                                self.tftp_sock.settimeout(None)
                            except socket.timeout:
                                # Timeout waiting for packet - might be missing blocks
                                if expected_size is not None and total_received < expected_size:
                                    missing_bytes = expected_size - total_received
                                    self.tftp_msg_queue.put(f"⚠️ TIMEOUT: Expected more data. Missing approximately {missing_bytes} bytes.\n")
                                    self.tftp_msg_queue.put(f"⚠️ This file appears to be CORRUPTED - some packets were not received!\n")
                                    self.tftp_msg_queue.put(f"⚠️ Please request the sender to send the file again.\n")
                                break
                                
                            if addr_check != addr:
                                continue
                            pkt_opcode = struct.unpack('!H', data_pkt[:2])[0]
                            if pkt_opcode != 3:  # DATA
                                break
                            block = struct.unpack('!H', data_pkt[2:4])[0]
                            
                            # Check for missing blocks
                            if block != block_num:
                                if block > block_num:
                                    # We're missing some blocks
                                    for missing in range(block_num, block):
                                        missing_blocks.append(missing)
                                        self.tftp_msg_queue.put(f"⚠️ MISSING BLOCK {missing}! Expected {block_num}, received {block}\n")
                                    consecutive_missing = block - block_num
                                    block_num = block
                                else:
                                    # Duplicate or out-of-order block
                                    self.tftp_msg_queue.put(f"⚠️ Duplicate/out-of-order block {block}, expected {block_num}\n")
                                    continue
                            
                            received_blocks.append(block)
                            filedata = data_pkt[4:]
                            f.write(filedata)
                            total_received += len(filedata)
                            last_received_block = block
                            
                            if missing_blocks:
                                self.tftp_msg_queue.put(f"Received block {block_num} ({len(filedata)} bytes) - GAPS DETECTED\n")
                            else:
                                self.tftp_msg_queue.put(f"Received block {block_num}, {len(filedata)} bytes\n")
                            
                            # ACK
                            ack_pkt = struct.pack('!HH', 4, block_num)
                            self.tftp_sock.sendto(ack_pkt, addr)
                            block_num += 1
                            
                            if len(filedata) < 512:
                                break
                    
                    # Final corruption check
                    if missing_blocks:
                        self.tftp_msg_queue.put(f"\n🚨 FILE CORRUPTION DETECTED! 🚨\n")
                        self.tftp_msg_queue.put(f"Missing blocks: {missing_blocks}\n")
                        self.tftp_msg_queue.put(f"Missing approximately {len(missing_blocks) * 512} bytes of data.\n")
                        self.tftp_msg_queue.put(f"⚠️ This file is CORRUPTED and should not be used!\n")
                        self.tftp_msg_queue.put(f"⚠️ Please request the sender to resend the file.\n\n")
                    
                    # Check size if expected
                    if expected_size is not None:
                        if total_received != expected_size:
                            missing_bytes = expected_size - total_received
                            self.tftp_msg_queue.put(f"🚨 SIZE MISMATCH DETECTED! 🚨\n")
                            self.tftp_msg_queue.put(f"Expected {expected_size} bytes, received {total_received} bytes\n")
                            self.tftp_msg_queue.put(f"Missing {missing_bytes} bytes - FILE IS CORRUPTED!\n")
                            self.tftp_msg_queue.put(f"⚠️ Please request the sender to send the file again.\n")
                        else:
                            if missing_blocks:
                                self.tftp_msg_queue.put(f"File size matches expected ({total_received} bytes) but blocks are missing - FILE IS STILL CORRUPTED!\n")
                            else:
                                self.tftp_msg_queue.put(f"File received successfully: {out_filename} ({total_received} bytes, matches expected)\n")
                    else:
                        if missing_blocks:
                            self.tftp_msg_queue.put(f"File received: {out_filename} ({total_received} bytes) - ⚠️ BUT CORRUPTED DUE TO MISSING BLOCKS!\n")
                        else:
                            self.tftp_msg_queue.put(f"File received: {out_filename} ({total_received} bytes)\n")
            except Exception as e:
                if self.tftp_listening:
                    self.tftp_msg_queue.put(f"Error: {str(e)}\n")
    
    def open_listen_popup(self):
        # This method is no longer used but kept for compatibility
        pass
    
    def open_write_popup(self):
        UDPWritePopup(self)
    
    def poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.udp_text.config(state='normal')
                self.udp_text.insert(tk.END, msg)
                self.udp_text.config(state='disabled')
                self.udp_text.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)
    
    def browse_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
    
    def start_sending(self):
        self.sending = True
        self.abort_flag = False
        self.normal_send_btn.config(state='disabled')
        self.swap_send_btn.config(state='disabled')
        self.fail_outoforder_btn.config(state='disabled')
        self.fail_duplicate_btn.config(state='disabled')
        self.fail_wrongnum_btn.config(state='disabled')
        self.fail_truncated_btn.config(state='disabled')
        self.fail_timeout_btn.config(state='disabled')
        self.fail_pktloss_btn.config(state='disabled')
        self.abort_frame.pack(pady=5, before=self.tftp_text_frame)
        self.progress.pack(pady=5, before=self.tftp_text_frame)
        self.progress.start()
        self.tftp_msg_queue.put("Sending...\n")
        # Disable mode switching during send
        self.send_radio.config(state='disabled')
        self.listen_radio.config(state='disabled')
    
    def stop_sending(self):
        self.tftp_msg_queue.put("Cleaning up send UI...\n")
        self.sending = False
        self.normal_send_btn.config(state='normal')
        self.swap_send_btn.config(state='normal')
        self.fail_outoforder_btn.config(state='normal')
        self.fail_duplicate_btn.config(state='normal')
        self.fail_wrongnum_btn.config(state='normal')
        self.fail_truncated_btn.config(state='normal')
        self.fail_timeout_btn.config(state='normal')
        self.fail_pktloss_btn.config(state='normal')
        self.abort_frame.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()
        # Re-enable mode switching after send
        self.send_radio.config(state='normal')
        self.listen_radio.config(state='normal')
    
    def abort_send(self):
        self.abort_flag = True
        self.tftp_msg_queue.put("Aborting send...\n")
        if self.tftp_sock:
            self.tftp_sock.close()
            self.tftp_sock = None
    
    def _send_tftp_worker(self, ip, filename_req, file_data, total_bytes):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            # WRQ packet with options
            opcode = 2
            mode = b'octet'
            wrq = struct.pack('!H', opcode) + filename_req.encode() + b'\0' + mode + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            self.tftp_msg_queue.put(f"Sent WRQ with size {total_bytes}\n")
            
            # Receive OACK or ACK 0
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
                except OSError:
                    if self.abort_flag:
                        raise Exception("Aborted during WRQ response")
                    raise
            if not received_resp:
                raise Exception("Aborted during WRQ response")
            
            resp_opcode = struct.unpack('!H', data[:2])[0]
            if resp_opcode not in (4, 6):
                raise Exception("Unexpected response to WRQ")
            if resp_opcode == 6:
                # Parse OACK options (optional, for confirmation)
                opt_data = data[2:]
                confirmed_size = None
                while len(opt_data) > 0:
                    key_end = opt_data.find(b'\0')
                    if key_end == -1:
                        break
                    key = opt_data[:key_end].decode()
                    opt_data = opt_data[key_end + 1:]
                    val_end = opt_data.find(b'\0')
                    if val_end == -1:
                        break
                    val = opt_data[:val_end].decode()
                    opt_data = opt_data[val_end + 1:]
                    if key == 'size':
                        confirmed_size = int(val)
                self.tftp_msg_queue.put(f"Received OACK with confirmed size {confirmed_size}\n")
            
            # Send file in blocks
            pos = 0
            block_num = 1
            while pos < len(file_data) and not self.abort_flag:
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                data_pkt = struct.pack('!HH', 3, block_num) + block
                sock.sendto(data_pkt, addr)
                
                hex_data = binascii.hexlify(block).decode()
                if len(hex_data) > 200:
                    hex_data = hex_data[:200] + '...'
                self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes): {hex_data}\n")
                
                # Wait for ACK
                received_ack = False
                ack = None
                while not self.abort_flag and not received_ack:
                    try:
                        ack, _ = sock.recvfrom(1024)
                        received_ack = True
                    except BlockingIOError:
                        time.sleep(0.01)
                        continue
                    except OSError:
                        if self.abort_flag:
                            break
                        raise
                
                if not received_ack:
                    break
                
                if struct.unpack('!HH', ack[:4])[0] != 4 or struct.unpack('!H', ack[2:4])[0] != block_num:
                    raise Exception("ACK mismatch")
                
                pos += 512
                block_num += 1
            
            if self.abort_flag:
                self.tftp_msg_queue.put(f"Upload aborted: {pos} bytes sent\n")
            else:
                self.tftp_msg_queue.put(f"Upload complete: {total_bytes} bytes\n")
        except Exception as e:
            if self.abort_flag:
                self.tftp_msg_queue.put(f"Upload aborted\n")
            else:
                self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            # Signal the main thread to stop sending UI
            self._stop_sending_flag = True
    
    def _send_tftp_worker_out_of_order(self, ip, filename_req, file_data, total_bytes):
        """Send blocks out of order (every 4th and 5th block swapped)"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            self.tftp_msg_queue.put(f"Sent WRQ with size {total_bytes}\n")
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            # Prepare all blocks
            blocks = []
            pos = 0
            block_num = 1
            while pos < len(file_data):
                block_end = min(pos + 512, len(file_data))
                blocks.append((block_num, file_data[pos:block_end]))
                pos += 512
                block_num += 1
            
            # Send blocks with some out of order
            idx = 0
            while idx < len(blocks) and not self.abort_flag:
                # Every 3rd and 4th block swap order
                if idx < len(blocks) - 1 and (idx + 1) % 4 == 3:
                    # Send block idx+1 first, then idx
                    for b_idx in [idx + 1, idx]:
                        block_num, block = blocks[b_idx]
                        data_pkt = struct.pack('!HH', 3, block_num) + block
                        sock.sendto(data_pkt, addr)
                        self.tftp_msg_queue.put(f"Sent block {block_num} OUT OF ORDER ({len(block)} bytes)\n")
                        # Wait for ACK
                        ack = None
                        while not self.abort_flag:
                            try:
                                ack, _ = sock.recvfrom(1024)
                                break
                            except BlockingIOError:
                                time.sleep(0.01)
                    idx += 2
                else:
                    block_num, block = blocks[idx]
                    data_pkt = struct.pack('!HH', 3, block_num) + block
                    sock.sendto(data_pkt, addr)
                    self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                    # Wait for ACK
                    while not self.abort_flag:
                        try:
                            ack, _ = sock.recvfrom(1024)
                            break
                        except BlockingIOError:
                            time.sleep(0.01)
                    idx += 1
            
            self.tftp_msg_queue.put(f"Out-of-order upload complete\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def _send_tftp_worker_duplicate(self, ip, filename_req, file_data, total_bytes):
        """Send some blocks twice"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            pos = 0
            block_num = 1
            while pos < len(file_data) and not self.abort_flag:
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                data_pkt = struct.pack('!HH', 3, block_num) + block
                sock.sendto(data_pkt, addr)
                self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                
                # Send duplicate for every 5th block
                if block_num % 5 == 0:
                    time.sleep(0.05)
                    sock.sendto(data_pkt, addr)
                    self.tftp_msg_queue.put(f"Sent DUPLICATE block {block_num}\n")
                
                # Wait for ACK
                while not self.abort_flag:
                    try:
                        ack, _ = sock.recvfrom(1024)
                        break
                    except BlockingIOError:
                        time.sleep(0.01)
                
                pos += 512
                block_num += 1
            
            self.tftp_msg_queue.put(f"Duplicate blocks upload complete\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def _send_tftp_worker_wrong_numbers(self, ip, filename_req, file_data, total_bytes):
        """Send blocks with wrong block numbers"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            pos = 0
            block_num = 1
            while pos < len(file_data) and not self.abort_flag:
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                
                # Use wrong block number for every 7th block
                wrong_num = block_num + 10 if block_num % 7 == 0 else block_num
                data_pkt = struct.pack('!HH', 3, wrong_num) + block
                sock.sendto(data_pkt, addr)
                
                if wrong_num != block_num:
                    self.tftp_msg_queue.put(f"Sent block with WRONG NUMBER {wrong_num} (should be {block_num})\n")
                else:
                    self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                
                # Wait for ACK (may fail due to wrong block number)
                try:
                    sock.settimeout(1.0)
                    ack, _ = sock.recvfrom(1024)
                    sock.settimeout(None)
                except:
                    sock.settimeout(None)
                    self.tftp_msg_queue.put(f"No ACK received for block {block_num}\n")
                
                pos += 512
                block_num += 1
            
            self.tftp_msg_queue.put(f"Wrong block numbers upload complete\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def _send_tftp_worker_truncated(self, ip, filename_req, file_data, total_bytes):
        """Stop transfer after 60% of file"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            self.tftp_msg_queue.put(f"Sent WRQ with size {total_bytes} (will truncate at 60%)\n")
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            truncate_at = int(len(file_data) * 0.6)
            pos = 0
            block_num = 1
            while pos < truncate_at and not self.abort_flag:
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                data_pkt = struct.pack('!HH', 3, block_num) + block
                sock.sendto(data_pkt, addr)
                self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                
                # Wait for ACK
                while not self.abort_flag:
                    try:
                        ack, _ = sock.recvfrom(1024)
                        break
                    except BlockingIOError:
                        time.sleep(0.01)
                
                pos += 512
                block_num += 1
            
            self.tftp_msg_queue.put(f"Transfer TRUNCATED at {pos} bytes (60% of {total_bytes})\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def _send_tftp_worker_timeout(self, ip, filename_req, file_data, total_bytes):
        """Pause for 10 seconds mid-transfer"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            pause_at_block = 5
            pos = 0
            block_num = 1
            while pos < len(file_data) and not self.abort_flag:
                # Pause at block 5
                if block_num == pause_at_block:
                    self.tftp_msg_queue.put(f"⏸️ PAUSING for 10 seconds to simulate timeout...\n")
                    time.sleep(10)
                    self.tftp_msg_queue.put(f"▶️ Resuming transfer...\n")
                
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                data_pkt = struct.pack('!HH', 3, block_num) + block
                sock.sendto(data_pkt, addr)
                self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                
                # Wait for ACK
                while not self.abort_flag:
                    try:
                        ack, _ = sock.recvfrom(1024)
                        break
                    except BlockingIOError:
                        time.sleep(0.01)
                
                pos += 512
                block_num += 1
            
            self.tftp_msg_queue.put(f"Timeout simulation upload complete\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def _send_tftp_worker_packet_loss(self, ip, filename_req, file_data, total_bytes):
        """Randomly drop 30% of packets"""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            self.tftp_sock = sock
            
            wrq = struct.pack('!H', 2) + filename_req.encode() + b'\0' + b'octet' + b'\0size\0' + str(total_bytes).encode() + b'\0'
            sock.sendto(wrq, (ip, 69))
            self.tftp_msg_queue.put(f"Sent WRQ - will drop ~30% of packets randomly\n")
            
            # Wait for OACK/ACK
            received_resp = False
            while not self.abort_flag and not received_resp:
                try:
                    data, addr = sock.recvfrom(1024)
                    received_resp = True
                except BlockingIOError:
                    time.sleep(0.01)
                    continue
            
            pos = 0
            block_num = 1
            dropped_count = 0
            while pos < len(file_data) and not self.abort_flag:
                block_end = min(pos + 512, len(file_data))
                block = file_data[pos:block_end]
                
                # 30% chance to drop packet
                if random.random() < 0.3:
                    self.tftp_msg_queue.put(f"🔴 DROPPED packet for block {block_num}\n")
                    dropped_count += 1
                else:
                    data_pkt = struct.pack('!HH', 3, block_num) + block
                    sock.sendto(data_pkt, addr)
                    self.tftp_msg_queue.put(f"Sent block {block_num} ({len(block)} bytes)\n")
                    
                    # Wait for ACK
                    while not self.abort_flag:
                        try:
                            ack, _ = sock.recvfrom(1024)
                            break
                        except BlockingIOError:
                            time.sleep(0.01)
                
                pos += 512
                block_num += 1
            
            self.tftp_msg_queue.put(f"Packet loss simulation complete - dropped {dropped_count} packets\n")
        except Exception as e:
            self.tftp_msg_queue.put(f"Error: {str(e)}\n")
        finally:
            if sock:
                sock.close()
            self.tftp_sock = None
            self._stop_sending_flag = True
    
    def normal_send_tftp(self):
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting normal TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def swap_send_tftp(self):
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting swap TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        if total_bytes > 1:
            pos1 = random.randint(total_bytes // 4, 3 * total_bytes // 4)
            pos2 = random.randint(total_bytes // 4, 3 * total_bytes // 4)
            while pos2 == pos1:
                pos2 = random.randint(total_bytes // 4, 3 * total_bytes // 4)
            file_data[pos1], file_data[pos2] = file_data[pos2], file_data[pos1]
            self.tftp_msg_queue.put(f"Swapped bytes at positions {pos1} and {pos2}\n")
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_out_of_order(self):
        """Send blocks out of order"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting out-of-order TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_out_of_order, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_duplicate(self):
        """Send some blocks twice"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting duplicate blocks TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_duplicate, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_wrong_numbers(self):
        """Send blocks with wrong block numbers"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting wrong block numbers TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_wrong_numbers, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_truncated(self):
        """Stop transfer early (truncated)"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting truncated TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_truncated, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_timeout(self):
        """Pause mid-transfer to simulate timeout"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting timeout TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_timeout, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def failure_packet_loss(self):
        """Randomly drop packets"""
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting packet loss TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        total_bytes = len(file_data)
        filename_req = os.path.basename(filename)
        self.tftp_thread = threading.Thread(target=self._send_tftp_worker_packet_loss, args=(ip, filename_req, file_data, total_bytes), daemon=True)
        self.tftp_thread.start()
    
    def toggle_udp(self):
        if not self.udp_running:
            port = int(self.port_entry.get())
            try:
                self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_sock.bind(('0.0.0.0', port))
                self.udp_running = True
                self.open_btn.config(text="UDP Close")
                self.udp_thread = threading.Thread(target=self.udp_listen, daemon=True)
                self.udp_thread.start()
                self.msg_queue.put(f"Listening on port {port}\n")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            self.udp_running = False
            if self.udp_sock:
                self.udp_sock.close()
            self.open_btn.config(text="UDP Open")
            self.msg_queue.put("Stopped listening\n")
    
    def udp_listen(self):
        while self.udp_running:
            try:
                data, addr = self.udp_sock.recvfrom(1024)
                timestamp = datetime.now().strftime("%H:%M:%S")
                hex_data = binascii.hexlify(data).decode()[:100] + ('...' if len(data) > 50 else '')
                ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)[:100] + ('...' if len(data) > 100 else '')
                self.msg_queue.put(f"[{timestamp}] {addr[0]:<15}:{addr[1]:<5}\n  HEX: {hex_data}\n  ASCII: {ascii_data}\n\n")
            except:
                break
    
    def on_closing(self):
        if self.udp_running:
            self.udp_running = False
            if self.udp_sock:
                self.udp_sock.close()
        if self.tftp_listening:
            self.tftp_listening = False
            if self.tftp_sock:
                self.tftp_sock.close()
        if self.sending:
            self.abort_flag = True
            if self.tftp_sock:
                self.tftp_sock.close()
                self.tftp_sock = None
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TFTPUDPApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    #Fountation Comit
    