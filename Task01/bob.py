#!/usr/bin/python3

import socket

#  -- Небольшой сервачок для наших целей
class Server():
    #  --  Инициализация клиента  --
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = socket.socket()
        self.socket.bind((self.address, self.port))
        self.socket.listen(1)
        self.connection, self.conn_address = self.socket.accept()
    #  --  Приём от клиента  --
    def read(self):
        data = b""
        while (not data) or (data[-1] == b'\n'):
            data += self.connection.recv(1024)
        return data.decode("utf-8")[:-1]
    #  --  Отправка клиенту  --
    def send(self, data):
        data += "\n"
        self.connection.send(data.encode("utf-8"))
    #  --  Отключение клиента  --
    def close(self):
        self.connection.close()

#  -- основная функция --
def main():
    bob = Server("", 9999)
    print(bob.read())
    bob.send("Hello Alice!")
    bob.close()

if __name__ == "__main__":
    main()
