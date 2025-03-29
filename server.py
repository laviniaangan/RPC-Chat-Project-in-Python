import rpyc
from rpyc.utils.server import ThreadedServer
from threading import Lock

class ChatService(rpyc.Service):
    def __init__(self):
        self.messages = []  # Lista de mesaje
        self.clients = []   # Lista de clienți conectați
        self.lock = Lock()  # Pentru sincronizare

    def on_connect(self, conn):
        """Se apelează când un client se conectează"""
        with self.lock:
            print(f"New client connected: {conn}")
            self.clients.append(conn)
            print(f"Total clients connected: {len(self.clients)}")
            # Trimite mesajele existente clientului nou conectat
            for msg in self.messages:
                try:
                    conn.root.receive_message(msg)
                except Exception as e:
                    print(f"Failed to send history to new client: {e}")

    def on_disconnect(self, conn):
        """Se apelează când un client se deconectează"""
        with self.lock:
            print(f"Client disconnected: {conn}")
            if conn in self.clients:
                self.clients.remove(conn)
            print(f"Total clients connected: {len(self.clients)}")

    def exposed_send_message(self, sender, message):
        """Metodă expusă pentru trimiterea mesajelor"""
        with self.lock:
            formatted_message = f"[{sender}]: {message}"
            self.messages.append(formatted_message)
            print(f"Received message: {formatted_message}")
            self.broadcast_message(formatted_message)
            return f"Message from {sender} received"

    def exposed_get_messages(self, last_index):
        """Metodă expusă pentru obținerea mesajelor noi"""
        with self.lock:
            if last_index < 0 or last_index >= len(self.messages):
                last_index = -1
            new_messages = self.messages[last_index + 1:]
            return new_messages, len(self.messages) - 1

    def broadcast_message(self, message):
        """Trimite mesajul către toți clienții conectați"""
        with self.lock:
            print(f"Broadcasting message to {len(self.clients)} clients: {message}")
            disconnected_clients = []
            for client in self.clients:
                try:
                    client.root.receive_message(message)
                except Exception as e:
                    print(f"Failed to send to a client: {e}")
                    disconnected_clients.append(client)
            
            # Elimină clienții deconectați
            for client in disconnected_clients:
                if client in self.clients:
                    self.clients.remove(client)
            print(f"Total clients after broadcast: {len(self.clients)}")

if __name__ == "__main__":
    server = ThreadedServer(ChatService, port=18813, reuse_addr=True)
    print("Starting RPC Chat Server on port 18813...")
    server.start()