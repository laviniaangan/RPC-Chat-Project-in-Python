import rpyc
import threading
import time
import tkinter as tk
from tkinter import scrolledtext
import socket

class ClientService(rpyc.Service):
    def exposed_receive_message(self, message):
        """Metodă expusă pentru primirea mesajelor de la server"""
        if app:
            app.display_message(f"Received: {message}")

class ChatApp:
    def __init__(self, root, client_name):
        self.root = root
        self.client_name = client_name
        self.root.title(f"Chat Client - {client_name}")
        self.conn = None  # Initialize conn as None
        self.is_connected = False  # Track connection status
        
        # Configurare interfață
        self.chat_area = scrolledtext.ScrolledText(root, width=50, height=20, wrap=tk.WORD)
        self.chat_area.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        self.input_field = tk.Entry(root, width=40)
        self.input_field.grid(row=1, column=0, padx=10, pady=10)
        self.input_field.bind("<Return>", lambda event: self.send_message())  # Trimitere cu Enter
        
        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)
        
        # Încercare de conectare la server cu retry
        self.connect_to_server_with_retry()
        if not self.conn:
            self.display_message("Failed to connect to server. Please ensure the server is running and try again.")
            return
        
        self.display_message(f"Connected as {client_name}. Type your message below.")
        
        # Variabile pentru polling
        self.last_index = -1
        self.stop_polling = False
        
        # Pornește polling-ul mesajelor
        self.polling_thread = threading.Thread(target=self.poll_messages)
        self.polling_thread.daemon = True
        self.polling_thread.start()
        
        # Gestionare închidere fereastră
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def connect_to_server_with_retry(self, max_retries=3, retry_delay=5):
        """Încercă să se conecteze la server cu retry"""
        for attempt in range(max_retries):
            try:
                # Configurare timeout-uri mai lungi
                self.conn = rpyc.connect(
                    "localhost", 
                    18813, 
                    service=ClientService, 
                    config={
                        "sync_request_timeout": 30,  # 30 secunde pentru cereri sincrone
                        "allow_public_attrs": True,
                        "allow_pickle": True
                    }
                )
                self.is_connected = True
                self.display_message(f"Successfully connected to server on attempt {attempt + 1}.")
                return
            except (socket.timeout, TimeoutError, ConnectionRefusedError) as e:
                self.display_message(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    self.display_message(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
        self.display_message("Could not connect to server after maximum retries.")
        self.is_connected = False

    def display_message(self, message):
        """Afișează un mesaj în zona de chat"""
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)  # Derulează automat la ultimul mesaj
    
    def send_message(self):
        """Trimite mesajul introdus către server"""
        if not self.is_connected or not self.conn:
            self.display_message("Cannot send message: Not connected to server.")
            return
        message = self.input_field.get().strip()
        if message:
            try:
                response = self.conn.root.send_message(self.client_name, message)
                self.display_message(f"Server: {response}")
                self.input_field.delete(0, tk.END)
            except Exception as e:
                self.display_message(f"Error sending message: {e}")
                if "result expired" in str(e) or "connection" in str(e).lower():
                    self.is_connected = False
                    self.display_message("Connection lost. Attempting to reconnect...")
                    self.reconnect()
    
    def poll_messages(self):
        """Verifică periodic mesajele noi de la server"""
        while not self.stop_polling:
            if not self.is_connected or not self.conn:
                time.sleep(5)  # Așteaptă înainte de a încerca reconectarea
                self.reconnect()
                continue
            try:
                new_messages, new_index = self.conn.root.get_messages(self.last_index)
                for msg in new_messages:
                    self.display_message(f"Received: {msg}")
                self.last_index = new_index
            except Exception as e:
                self.display_message(f"Error polling messages: {e}")
                if "result expired" in str(e) or "connection" in str(e).lower():
                    self.is_connected = False
                    self.display_message("Connection lost. Attempting to reconnect...")
                    self.reconnect()
            time.sleep(2)  # Reducem frecvența polling-ului la 2 secunde
    
    def reconnect(self):
        """Încearcă să se reconecteze la server"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        self.conn = None
        self.connect_to_server_with_retry()
        if self.is_connected:
            self.last_index = -1  # Resetează indexul pentru a primi toate mesajele noi
    
    def on_closing(self):
        """Închide conexiunea și fereastra"""
        self.stop_polling = True
        if self.polling_thread.is_alive():
            self.polling_thread.join()
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        self.root.destroy()

def run_client(client_name):
    global app
    root = tk.Tk()
    app = ChatApp(root, client_name)
    root.mainloop()

if __name__ == "__main__":
    client_name = input("Enter your name: ")
    run_client(client_name)