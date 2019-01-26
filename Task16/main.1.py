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


def Alice(bob, args):
    global NAME
    NAME = "Alice"
    net = NeuralNet()
    print(log("Ключ в сети {}".format(net.weights)))
    rnd = 1
    while True:
        X = NeuralNet.randominput()
        Za = net.analyse(X)
        bob.send((X, Za))
        Zb = bob.recv()
        if Za == Zb:
            net.reinforce(X, Za)
            t = "{} Раунд".format(rnd)
            print(t + "-"* (60 - len(t)))
            print(log("Ключ в сети {} Z={}".format(net.weights, Za)))
            key = NeuralNet.arraytokey(net.weights).to_bytes(1, "little")
            key += b'\0'*15
            cipher = AES.new(key, 1)
            bob.send(cipher.encrypt(MESS))
            if bob.recv():
                print(log("Обмен ключами завершён"))
                break
        else:
            t = "{} Раунд".format(rnd)
            print(t + "-"* (60 - len(t)))
            print(log("Ключ в сети {} Z={}".format(net.weights, Za)))
            bob.send(1)
        rnd += 1

def Bob(alice, args):
    global NAME
    NAME = "Bob"
    net = NeuralNet()
    print(log("Ключ в сети {}".format(net.weights)))
    while True:
        X, Za = alice.recv()
        Zb = net.analyse(X)
        alice.send(Zb)
        if Za == Zb:
            net.reinforce(X, Zb)
            key = NeuralNet.arraytokey(net.weights).to_bytes(1, "little")
            key += b'\0'*15
            cipher = AES.new(key, 1)
            M = alice.recv()
            print(log("Ключ в сети {} Z={}".format(net.weights, Zb)))
            M = cipher.decrypt(M)
            if MESS == M:
                print(log("Ключи совпали MESS={} получено".format(M.decode("utf-8"))))
                alice.send(1)
                break
            else:
                alice.send(0)
        else:
            alice.recv()
            print(log("Ключ в сети {} Z={}".format(net.weights, Zb)))

def main(args):
    AB, BA = Pipe(True)
    alice = Process(target=Alice, args=(AB, args))
    bob = Process(target=Bob, args=(BA, args))
    alice.start()
    bob.start()
    alice.join()
    bob.join()
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Протокол обмена ключом 8bit через нейросеть"
        )
    main(parser.parse_args())
