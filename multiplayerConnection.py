import socket
import threading


def getLocalIP():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class Server:
    def __init__(self, ip="0.0.0.0", port=5555, on_client_connected=None):
        self.ip                  = ip
        self.port                = port
        self.server              = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clientSocket        = None
        self.clientAddress       = None
        self.on_client_connected = on_client_connected
        self.clientConnected     = False

    def startAsyncServer(self):
        thread = threading.Thread(target=self._setupServerConnection, daemon=True)
        thread.start()

    def _setupServerConnection(self):
        try:
            self.server.bind((self.ip, self.port))
            self.server.listen(1)
            print(f"[SERVER] Listening on {getLocalIP()}:{self.port}")
            self.clientSocket, self.clientAddress = self.server.accept()
            print(f"[SERVER] Client connected from {self.clientAddress}")
            self.clientConnected = True
            if self.on_client_connected:
                self.on_client_connected()
            threading.Thread(target=self._listenToClient, daemon=True).start()
        except Exception as e:
            print(f"[SERVER ERROR] {e}")

    def _listenToClient(self):
        while True:
            try:
                data = self.clientSocket.recv(1024)
                if not data:
                    break
                print(f"[CLIENT] {data.decode('utf-8')}")
            except ConnectionResetError:
                print("[SERVER] Client disconnected.")
                break
        self.clientConnected = False


class Client:
    def __init__(self, ip="127.0.0.1", port=5555):
        self.ip     = ip
        self.port   = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def setupClientConnection(self):
        try:
            self.socket.connect((self.ip, self.port))
            print(f"[CLIENT] Connected to {self.ip}:{self.port}")
            threading.Thread(target=self._listenToServer, daemon=True).start()
            return self.socket, True
        except Exception as e:
            print(f"[CLIENT ERROR] Could not connect: {e}")
            return None, False

    def _listenToServer(self):
        while True:
            try:
                msg = self.socket.recv(1024).decode("utf-8")
                if not msg:
                    break
                print(f"[SERVER MESSAGE] {msg}")
            except ConnectionResetError:
                print("[CLIENT] Server disconnected.")
                break
