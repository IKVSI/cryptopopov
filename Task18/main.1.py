#!/usr/bin/python3

import argparse
import sys
from multiprocessing import Process, Pipe
import Cryptodome.Random.random as random
from Cryptodome.Cipher import AES

NAME="MASTER"
MESS = b"Secret message!\0"

def log(message):
    return NAME + (7-len(NAME))*" "+": "+message

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()


class NeuralNet():
    #  --  Разбивка на биты  --
    @staticmethod
    def keytoarray(key):
        X = []
        k = 128
        for _ in range(8):
            X.append( 1 if k & key else -1 )
            k >>= 1
        return X
    
    #  --  Собираем из битов  --
    @staticmethod
    def arraytokey(X):
        key = 0
        k = 3**7
        for i in range(8):
            if X[i] == 0:
                key += k
            if X[i] == 1:
                key += 2*k
            k //= 3
        return key % 256

    @staticmethod
    def randominput():
        b = random.randint(0, 255)
        return NeuralNet.keytoarray(b)

    def __init__(self):
        self.weights = NeuralNet.randominput()

    #  --  Обработка входных данных  --
    def analyse(self, X):
        Y = 0
        for i in range(len(self.weights)):
            Y += X[i] * self.weights[i]
        return 1 if Y > 0 else -1
    
    def reinforce(self, X, Z):
        for i in range(len(X)):
            w = self.weights[i] + X[i]*Z
            if abs(w) < 2:
                self.weights[i] = w



def Alice(bob, eva, args):
    global NAME
    NAME = "Alice"
    for _ in range(args.n):
        net = NeuralNet()
        bobend = False
        evaend = False
        while True:
            X = NeuralNet.randominput()
            Za = net.analyse(X)
            bob.send((X, Za))
            eva.send((X, Za))
            Zb = bob.recv()
            if Za == Zb:
                net.reinforce(X, Za)
                key = NeuralNet.arraytokey(net.weights).to_bytes(1, "little")
                key += b'\0'*15
                cipher = AES.new(key, 1)
                if not bobend:
                    bob.send(cipher.encrypt(MESS))
                    if bob.recv():
                        bobend = True
                if not evaend:
                    eva.send(cipher.encrypt(MESS))
                    if eva.recv():
                        evaend = True
            if bobend and evaend:
                break

def Bob(alice, eva, args):
    global NAME
    NAME = "Bob"
    for _ in range(args.n):
        net = NeuralNet()
        bobend = False
        evaend = False
        while True:
            X, Za = alice.recv()
            Zb = net.analyse(X)
            alice.send(Zb)
            eva.send(Zb)
            if Za == Zb:
                net.reinforce(X, Zb)
                if not bobend:
                    key = NeuralNet.arraytokey(net.weights).to_bytes(1, "little")
                    key += b'\0'*15
                    cipher = AES.new(key, 1)
                    M = alice.recv()
                    M = cipher.decrypt(M)
                    if MESS == M:
                        alice.send(1)
                        eva.send(1)
                        bobend = True
                    else:
                        alice.send(0)
                        eva.send(0)
                if not evaend:
                    if eva.recv():
                        evaend = True
            if bobend and evaend:
                break



def Eva(alice, bob, args):
    global NAME
    NAME = "Eva"
    BRND = 0
    ERND = 0
    for i in range(args.n):
        net = NeuralNet()
        rnd = 1
        bobrnd = 0
        evarnd = 0
        while True:
            X, Za = alice.recv()
            Zb = bob.recv()
            Ze = net.analyse(X)
            if Za == Zb:
                if Zb == Ze:
                    net.reinforce(X, Ze)
                if not evarnd:
                    key = NeuralNet.arraytokey(net.weights).to_bytes(1, "little")
                    key += b'\0'*15
                    cipher = AES.new(key, 1)
                    M = alice.recv()
                    M = cipher.decrypt(M)
                    if M == MESS:
                        evarnd = rnd
                        alice.send(1)
                        bob.send(1)
                    else:
                        alice.send(0)
                        bob.send(0)
                if not bobrnd:
                    if bob.recv():
                        bobrnd = rnd
            if bobrnd and evarnd:
                break
            rnd += 1
        BRND += bobrnd
        ERND += evarnd
        print(log("{}\t подход: Бобу потребовалось {} раундов, Еве {} раундов".format(str(i+1).zfill(len(str(args.n))), bobrnd, evarnd)))
    print("-"*60+"\n"+log("Итог: В среднем Бобу надо {} раундов, Еве {} раундов".format(BRND / args.n, ERND / args.n)))

def main(args):
    AB, BA = Pipe(True)
    AE, EA = Pipe(True)
    BE, EB = Pipe(True)
    alice = Process(target=Alice, args=(AB, AE, args))
    bob = Process(target=Bob, args=(BA, BE, args))
    eva = Process(target=Eva, args=(EA, EB, args))
    alice.start()
    bob.start()
    eva.start()
    alice.join()
    bob.join()
    eva.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Протокол обмена ключом 8bit через нейросеть, симуляция Евы"
        )
    parser.add_argument("-n", type=int, default=100, help="Количество ключей для обмена (запусков)")
    main(parser.parse_args())
