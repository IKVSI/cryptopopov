#!/usr/bin/python3

import socket
import random
import argparse
from sympy import sieve
from sympy.ntheory import factorint

CODEPAGE = "cp866"

class Sock():

    def __init__(self, address, port, server=False):
        self.address = address
        self.port = port
        self.data = b""
        if server:
            self.name = "Bob"
            sock = socket.socket()
            sock.bind((self.address, self.port))
            self.log("Ожидание подключения от Alice host={} port={}".format(self.address, self.port))
            sock.listen(1)
            self.connection, self.conn_address = sock.accept()
        else:
            self.name = "Alice"
            self.connection = socket.socket()
            self.connection.connect((self.address, self.port))
    
    #  --  Получение данных  --
    def read(self):
        # получаем длину сообщения
        while (len(self.data) < 8):
            self.data += self.connection.recv(8)
        size = int.from_bytes(self.data[:8], "little")
        self.data = self.data[8:]
        # дочитываем сообщение
        while (len(self.data) < size):
            self.data += self.connection.recv(1024)
        rdata = self.data[:size]
        self.data = self.data[size:]
        return rdata

    #  --  Отправка данных  --
    def send(self, dt):
        size = len(dt)
        # Отправим длину сообщения
        self.connection.send(size.to_bytes(8, "little"))
        # Отправим сообщение
        self.connection.send(dt)

    #  --  Отправка Инта  --
    def sendInt(self, number):
        self.send(number.to_bytes(number.bit_length() // 8 + 1, "little"))

    #  --  Получение Инта  --
    def readInt(self):
        return int.from_bytes(self.read(), "little")

    #  --  Закрытие соединения --
    def close(self):
        self.connection.close()
    
    #  --  Логи программы  --
    def log(self, message):
        print("{}: {}".format(self.name, message))

# Структура для преобразования данных
class Shamir():
    
    def __init__(self, prime=0, primeend=0):
        self.prime = prime
        if primeend and (primeend > prime):
            self.prime = random.choice([i for i in sieve.primerange(prime, primeend)])
        elif (not self.prime) or primeend:
            self.prime = random.choice([i for i in sieve.primerange(500, 1000)])
        #  --  Генерируем взаимнопростые числа с p-1  --
        self.keys = []
        self.p1 = self.prime - 1
        f = factorint(self.p1).keys()
        for i in range(3,self.prime,2):
            fl = True
            for j in f:
                if i%j == 0:
                    fl = False
                    break
            if fl:
                self.keys.append(i)
        self.blocksize = self.prime.bit_length() // 8
    
    def generate_key(self):
        self.encrypt = random.choice(self.keys)
        self.decrypt = None
        for i in self.keys:
            if (self.encrypt * i) % (self.p1) == 1:
                self.decrypt = i
                break

#  --  Обработка для Bob  --
def bob(args, conn):
    conn.log("Alice подключена на host={}, port={}".format(conn.address, conn.port))
    prime = conn.readInt()
    conn.log("Простое число prime={} получено".format(prime))
    sh = Shamir(prime)
    #  --  Получение сообщения блоками  --
    M = []
    i = 0
    print("-"*80)
    while True:
        sh.generate_key()
        conn.log("{} блок: Генерируем Eb={}, Db={} Eb*Db = 1 (mod p-1)".format(i+1, sh.encrypt, sh.decrypt))
        Mea = conn.readInt()
        conn.log("1 шаг ({} блок): Получаем M^Ea = {} (mod p)".format(i+1, Mea))
        Meaeb = pow(Mea, sh.encrypt, sh.prime)
        conn.sendInt(Meaeb)
        conn.log("2 шаг ({} блок): Отправляем M^Ea^Eb = {} (mod p)".format(i+1, Meaeb))
        Meb = conn.readInt()
        conn.log("3 шаг ({} блок): Получаем M^Eb = {} (mod p)".format(i+1, Meb))
        Mb = pow(Meb, sh.decrypt, sh.prime)
        conn.log("4 шаг ({} блок): Вычисляем M = {}".format(i+1, Mb))
        mblock = Mb.to_bytes(sh.blocksize, "little").decode(CODEPAGE)
        conn.log("{} блок: Преобразуем M = {} в \"{}\"".format(i+1, Mb, mblock))
        M.append(mblock)
        print("-"*80)
        if mblock[-1] == '\0':
            break
        i += 1
    message = "".join(M).replace('\0', '')
    conn.log("Сообщение \"{}\" получено от Alice".format(message))


#  --  Обработка для Alice --
def alice(args, conn):
    conn.log("Bob подключён на host={}, port={}".format(conn.address, conn.port))
    sh = Shamir(args.prime, args.primeend)
    conn.log("Сгенерированно простое число для обмена сообщением p={}".format(sh.prime))
    conn.sendInt(sh.prime)
    conn.log("Простое число p={} отправленно Bob-у".format(sh.prime))
    #  --  Отправка сообщения блоками  --
    M = " ".join(args.message)
    M += '\0'
    if len(M)%sh.blocksize:
        M += (sh.blocksize-len(M)%sh.blocksize)*'\0'
    #  --  Разбивка на блоки  --
    M = [M[i*sh.blocksize:i*sh.blocksize+sh.blocksize] for i in range(len(M)//sh.blocksize)]
    print("-"*80)
    for i in range(len(M)):
        mblock = M[i].encode(CODEPAGE)
        Mb = int.from_bytes(mblock, "little")
        conn.log("{} блок: Преобразуем \"{}\" в число M = {}".format(i+1, M[i], Mb))
        sh.generate_key()
        conn.log("{} блок: Генерируем Ea={}, Da={} Ea*Da = 1 (mod p-1)".format(i+1, sh.encrypt, sh.decrypt))
        Mea = pow(Mb, sh.encrypt, sh.prime)
        conn.sendInt(Mea)
        conn.log("1 шаг ({} блок): Отправляем M^Ea = {} (mod p)".format(i+1, Mea))
        Meaeb = conn.readInt()
        conn.log("2 шаг ({} блок): Получаем M^Ea^Eb = {} (mod p)".format(i+1, Meaeb))
        Meb = pow(Meaeb, sh.decrypt, sh.prime)
        conn.sendInt(Meb)
        conn.log("3 шаг ({} блок): Отправляем M^Ea^Eb^Da = M^Eb = {} (mod p)".format(i+1, Meb))
        conn.log("Закончена обработка {} блока".format(i+1))
        print("-"*80)
    conn.log("Сообщение \"{}\" отправлено Bob-у".format(" ".join(args.message)))


def main(args):
    conn = Sock(args.host, args.port, args.s)
    if args.s:
        bob(args, conn)
    else:
        alice(args, conn)
    conn.close()
    if args.p:
        print("\nПауза... Нажмите <Enter> для выхода ...")
        input()

if __name__ == "__main__":
    # -- получение аргументов строки --
    parser = argparse.ArgumentParser(
        description="Программа для ознакомления с работой протокола Шамира"
        )
    parser.add_argument("-s", action='store_true', help="Запуск сервера Bob")
    parser.add_argument("-port", default=9999, type=int, help="Порт для соединения или сервера")
    parser.add_argument("-host", default="127.0.0.1", type=str, help="Адрес подключения или сервера")
    parser.add_argument("-prime", default=0, type=int, help="Установить своё простое число для сообщения")
    parser.add_argument("-primeend", default=0, type=int, help="Если установлено это число, то простое будет взято из диапазона [prime, primeend]")
    parser.add_argument("-p", action='store_true', help="Пауза в конце программы")
    parser.add_argument("message", type=str, nargs="*", help="Сообщения используют однобайтовую кодировку (default = {})".format(CODEPAGE))
    main(parser.parse_args())

