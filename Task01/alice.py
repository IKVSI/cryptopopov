#!/usr/bin/python3

import socket

class Client():
    #  --  Подключение к серверу  --
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.connection = socket.socket()
        self.connection.connect((self.address, self.port))
    #  --  Приём от сервера  --
    def read(self):
        data = b""
        while (not data) or (data[-1] == b'\n'):
            data += self.connection.recv(1024)
        return data.decode("utf-8")[:-1]
    #  --  Отправка серверу  --
    def send(self, data):
        data += "\n"
        self.connection.send(data.encode("utf-8"))
    #  --  Отключение от сервера  --
    def close(self):
        self.connection.close()

#  -- основная функция --
def main():
    alice = Client("127.0.0.1", 9999)
    alice.send("Hello Bob!")
    print(alice.read())
    alice.close()

if __name__ == "__main__":
    main()
