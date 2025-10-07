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

class TFTPListenPopup:
    def __init__(self, parent):
        self.parent = parent
        self.popup = tk.Toplevel(parent.root)
        self.popup.title("TFTP Listen")
        self.popup.geometry("400x300")
        self.popup.configure(bg='black')
        
        tk.Label(self.popup, text="Listen IP:", fg='white', bg='black').pack(pady=5)
        self.listen_ip = tk.Entry(self.popup, width=20, bg='#404040', fg='white', insertbackground='white')
        self.listen_ip.pack(pady=5)
        self.listen_ip.insert(0, "10.10.2.46")  # Your Mac IP
        
        tk.Label(self.popup, text="Output File:", fg='white', bg='black').pack(pady=5)
        self.output_entry = tk.Entry(self.popup, width=50, bg='#404040', fg='white', insertbackground='white')
        self.output_entry.pack(pady=5)
        self.output_entry.insert(0, "received.bin")
        
        self.start_btn = tk.Button(self.popup, text="Start Listen", command=self.start_listen, bg='#404040', fg='black', relief='flat')
        self.start_btn.pack(pady=10)
        
        self.tftp_text = scrolledtext.ScrolledText(self.popup, height=15, state='disabled', bg='black', fg='white', insertbackground='white', font=('Arial', 12))
        self.tftp_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tftp_sock = None
        self.tftp_running = False
        self.msg_queue = queue.Queue()
        self.poll_queue()
    
    def poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                self.tftp_text.config(state='normal')
                self.tftp_text.insert(tk.END, msg)
                self.tftp_text.config(state='disabled')
                self.tftp_text.see(tk.END)
        except queue.Empty:
            pass
        self.popup.after(100, self.poll_queue)
    
    def start_listen(self):
        if not self.tftp_running:
            ip = self.listen_ip.get()
            filename = self.output_entry.get()
            try:
                self.tftp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.tftp_sock.bind((ip, 69))
                self.tftp_running = True
                self.start_btn.config(text="Stop Listen")
                self.tftp_thread = threading.Thread(target=self.tftp_server, args=(filename,), daemon=True)
                self.tftp_thread.start()
                self.msg_queue.put(f"Listening for TFTP on {ip}:69\n")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            self.tftp_running = False
            if self.tftp_sock:
                self.tftp_sock.close()
            self.start_btn.config(text="Start Listen")
            self.msg_queue.put("Stopped listening\n")
    
    def tftp_server(self, out_filename):
        while self.tftp_running:
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
                    
                    self.msg_queue.put(f"WRQ from {addr}: {filename_req} ({mode})\n")
                    
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
                        self.msg_queue.put(f"Sent OACK with expected size {expected_size}\n")
                    else:
                        ack = struct.pack('!HH', 4, 0)
                        self.tftp_sock.sendto(ack, addr)
                    
                    # Open file and receive
                    total_received = 0
                    with open(out_filename, 'wb') as f:
                        block_num = 1
                        while self.tftp_running:
                            data_pkt, addr_check = self.tftp_sock.recvfrom(1024)
                            if addr_check != addr:
                                continue
                            pkt_opcode = struct.unpack('!H', data_pkt[:2])[0]
                            if pkt_opcode != 3:  # DATA
                                break
                            block = struct.unpack('!H', data_pkt[2:4])[0]
                            if block != block_num:
                                break
                            filedata = data_pkt[4:]
                            f.write(filedata)
                            total_received += len(filedata)
                            self.msg_queue.put(f"Received block {block_num}, {len(filedata)} bytes\n")
                            
                            # ACK
                            ack_pkt = struct.pack('!HH', 4, block_num)
                            self.tftp_sock.sendto(ack_pkt, addr)
                            block_num += 1
                            if len(filedata) < 512:
                                break
                    
                    # Check size if expected
                    if expected_size is not None:
                        if total_received != expected_size:
                            self.msg_queue.put(f"Hey we just got the packet and its not the same number of bytes it said it was ({expected_size}), received {total_received}, its corrupted send again.\n")
                        else:
                            self.msg_queue.put(f"File received: {out_filename} ({total_received} bytes, matches expected)\n")
                    else:
                        self.msg_queue.put(f"File received: {out_filename} ({total_received} bytes)\n")
            except Exception as e:
                if self.tftp_running:
                    self.msg_queue.put(f"Error: {str(e)}\n")

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
        
        # Top half: TFTP Sender
        self.tftp_frame = tk.Frame(root, height=300, bg='#2c2c2c')
        self.tftp_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        tk.Label(self.tftp_frame, text="TFTP", font=('Arial', 16), fg='white', bg='#2c2c2c').pack(pady=10)
        
        ip_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        ip_frame.pack(pady=5)
        tk.Label(ip_frame, text="Target IP:", fg='white', bg='#2c2c2c').pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(ip_frame, width=20, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.ip_entry.pack(side=tk.LEFT, padx=5)
        self.ip_entry.insert(0, "10.10.2.46")  # Your Mac IP
        
        file_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        file_frame.pack(pady=5)
        tk.Label(file_frame, text="File:", fg='white', bg='#2c2c2c').pack(side=tk.LEFT)
        self.file_entry = tk.Entry(file_frame, width=40, bg='#404040', fg='white', insertbackground='white', font=('Arial', 12))
        self.file_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(file_frame, text="Browse", command=self.browse_file, bg='#404040', fg='black', relief='flat').pack(side=tk.LEFT, padx=5)
        
        btn_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        btn_frame.pack(pady=10)
        self.normal_send_btn = tk.Button(btn_frame, text="TFTP Send", command=self.normal_send_tftp, bg='#1a1a1a', fg='black', relief='flat')
        self.normal_send_btn.pack(side=tk.LEFT, padx=5)
        self.corrupt_send_btn = tk.Button(btn_frame, text="TFTP Corrupt Send", command=self.corrupt_send_tftp, bg='#ffaa00', fg='black', relief='flat')
        self.corrupt_send_btn.pack(side=tk.LEFT, padx=5)
        self.swap_send_btn = tk.Button(btn_frame, text="TFTP Swap Send", command=self.swap_send_tftp, bg='#00ff00', fg='black', relief='flat')
        self.swap_send_btn.pack(side=tk.LEFT, padx=5)
        self.listen_btn = tk.Button(btn_frame, text="TFTP Listen", command=self.open_listen_popup, bg='#1a1a1a', fg='black', relief='flat')
        self.listen_btn.pack(side=tk.LEFT, padx=5)
        
        # Abort button frame and progress, initially not packed
        self.abort_frame = tk.Frame(self.tftp_frame, bg='#2c2c2c')
        self.abort_btn = tk.Button(self.abort_frame, text="Abort Send", command=self.abort_send, bg='#ff0000', fg='white', relief='flat')
        self.abort_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(self.tftp_frame, mode='indeterminate', length=200)
        
        self.tftp_text = scrolledtext.ScrolledText(self.tftp_frame, height=8, state='disabled', bg='black', fg='white', insertbackground='white', font=('Arial', 10))
        self.tftp_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.poll_tftp_queue()
        
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
        
        self.udp_text = scrolledtext.ScrolledText(self.udp_frame, height=15, state='disabled', bg='black', fg='white', insertbackground='white', font=('Arial', 12))
        self.udp_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # UDP Socket
        self.udp_sock = None
        self.udp_thread = None
        self.udp_running = False
        self.msg_queue = queue.Queue()
        self.poll_queue()
    
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
    
    def open_listen_popup(self):
        TFTPListenPopup(self)
    
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
        self.corrupt_send_btn.config(state='disabled')
        self.swap_send_btn.config(state='disabled')
        self.abort_frame.pack(pady=5, before=self.tftp_text)
        self.progress.pack(pady=5, before=self.tftp_text)
        self.progress.start()
        self.tftp_msg_queue.put("Sending...\n")
    
    def stop_sending(self):
        self.sending = False
        self.normal_send_btn.config(state='normal')
        self.corrupt_send_btn.config(state='normal')
        self.swap_send_btn.config(state='normal')
        self.abort_frame.pack_forget()
        self.progress.stop()
        self.progress.pack_forget()
    
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
            self.root.after(0, self.stop_sending)
    
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
    
    def corrupt_send_tftp(self):
        if self.sending:
            return
        ip = self.ip_entry.get()
        filename = self.file_entry.get()
        if not ip or not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Invalid IP or file")
            return
        self.start_sending()
        self.tftp_msg_queue.put(f"Starting corrupt TFTP upload to {ip}: {filename}\n")
        with open(filename, 'rb') as f:
            file_data = bytearray(f.read())
        original_total = len(file_data)
        if original_total > 512:
            block_to_delete = random.randint(1, (original_total // 512) - 1)
            start_pos = (block_to_delete - 1) * 512
            end_pos = start_pos + 512
            del file_data[start_pos:end_pos]
            self.tftp_msg_queue.put(f"Deleted whole block {block_to_delete} (positions {start_pos} to {end_pos-1})\n")
        total_bytes = original_total
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
    