#!/usr/bin/python3

import argparse
import sys
import time
from multiprocessing import Process, Pipe
import Cryptodome.Random.random as random
from Cryptodome.Cipher import AES

NAME="MASTER"

def log(message):
    return NAME + (7-len(NAME))*" "+": "+message

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()

class NeuralNet():

    @staticmethod
    def analise(mess, dmess):
        positions = [ True for i in range(8) ]
        for i in range(len(mess)):
            sym = NeuralNet.inttoarray(mess[i])
            dsym = NeuralNet.inttoarray(dmess[i])
            for i in range(len(sym)):
                if sym[i] != dsym[i]:
                    positions[i] = False
            if True not in positions:
                break
        return positions


    #  --  Разбивка на биты  --
    @staticmethod
    def inttoarray(i):
        X = []
        k = 128
        for _ in range(8):
            X.append( 1 if k & i else 0 )
            k >>= 1
        return X
    
    #  --  Собираем из битов  --
    @staticmethod
    def arraytoint(X):
        i = 0
        k = 128
        for j in range(8):
            if X[j]:
                i += k
            k >>= 1
        return i

    def __init__(self, key):
        self.pweights = [ i for i in range(8) ]
        random.shuffle(self.pweights)
        self.weights = NeuralNet.inttoarray(key)
    
    def encrypt(self, text):
        ciphertext = b''
        for i in text:
            i = NeuralNet.inttoarray(i)
            for j in range(len(self.weights)):
                i[j] ^= self.weights[j]
            p = [i for i in range(8)]
            for j in range(len(self.pweights)):
                p[j] = i[self.pweights[j]]
            ciphertext += NeuralNet.arraytoint(p).to_bytes(1, "little")
        return ciphertext

    def decrypt(self, ciphertext):
        text = b''
        for i in ciphertext:
            i = NeuralNet.inttoarray(i)
            p = [i for i in range(8)]
            for j in range(len(self.pweights)):
                p[self.pweights[j]] = i[j]
            i = p
            for j in range(len(self.weights)):
                i[j] ^= self.weights[j]
            text += NeuralNet.arraytoint(p).to_bytes(1, "little")
        return text

    def reinforce(self, positions):
        p = []
        k = []
        for i in range(len(positions)):
            if not positions[i]:
                p.append(i)
        for i in self.pweights:
            if i in p:
                k.append(i)
        random.shuffle(k)
        j = 0
        for i in range(len(self.pweights)):
            if self.pweights[i] in k:
                self.pweights[i] = k[j]
                j += 1


def Alice(bob, eva, KEY, args):
    global NAME
    NAME = "Alice"
    net = NeuralNet(KEY)
    MESS =  [ i for i in range(256) ]
    random.shuffle(MESS)
    MESS = bytes(MESS)
    DMESS = net.encrypt(MESS)
    bob.send(DMESS)
    eva.send(DMESS)
    while True:
        DMESS = bob.recv()
        positions = NeuralNet.analise(MESS, DMESS)
        bob.send(positions)
        eva.send(positions)
        if False not in positions:
            break
    bob.recv()
    print(log("Все биты совпали, сеть готова для шифрования"))

def Bob(alice, eva, KEY, args):
    global NAME
    NAME = "Bob"
    net = NeuralNet(KEY)
    EMESS = alice.recv()
    print(log("KEY={} PKEY={}".format(net.weights, net.pweights)))
    while True:
        DMESS = net.decrypt(EMESS)
        alice.send(DMESS)
        eva.send(DMESS)
        positions = alice.recv()
        if False not in positions:
            break
        net.reinforce(positions)
    alice.send(1)

def genp(n, fl):
    p = []
    for i in n:
        if fl[i]:
            continue
        fl[i] = True
        t =  [i]
        tp = genp(n, fl)
        fl[i] = False
        if not tp:
            p.append(t)
        for j in tp:
            j.extend(t)
            p.append(j)
    return p


def Eva(alice, bob, args):
    global NAME
    NAME = "Eva"
    start_time = time.time()
    print(log("Генерируем сети для обучения"))
    net = []
    for i in range(256):
        net.append(NeuralNet(i))
    p = genp(tuple(i for i in range(8)), [False for i in range(8)])
    print(log("Получили зашифрованное сообщение Алисы"))
    EMESS = alice.recv()
    DMESS = bob.recv()
    rnd = 1
    print(log("Генерируем сеть боба по его проверочному сообщению {} раунда".format(rnd)))
    fl = False
    for i in range(256):
        print(log("Проверка сети номер {}".format(i)))
        for j in p:
            net[i].pweights = j
            if net[i].decrypt(EMESS) == DMESS:
                print(log("KEY={} PKEY={}".format(net[i].weights, net[i].pweights)))
                tnet = net[i]
                fl = True
                break
        if fl:
            break
    net = tnet
    print(log("Получена сеть с ключом KEY: ".format(net.weights)))
    while True:
        positions = alice.recv()
        p = []
        for i in positions:
            if i:
                p.append("+")
            else:
                p.append("-")
        print(log("Получены совпавшие позиции: 0:{} 1:{} 2:{} 3:{} 4:{} 5:{} 6:{} 7:{}".format(*p)))
        if False not in positions:
            break
        rnd += 1
        net.reinforce(positions)
        print(log("Получено проверочное сообщение боба {} раунда".format(rnd)))
        DMESS = bob.recv()
    end_time = time.time()
    tm = int(end_time - start_time)
    h = tm // 3600
    m = (tm % 3600) // 60
    s = tm % 60
    print("Затрачено времени на создание сети: {}h:{}m:{}s".format(h, m ,s))

def main(args):
    AB, BA = Pipe(True)
    AE, EA = Pipe(True)
    BE, EB = Pipe(True)
    KEY = random.randint(1, 254)
    alice = Process(target=Alice, args=(AB, AE, KEY, args))
    bob = Process(target=Bob, args=(BA, BE, KEY, args))
    eva = Process(target=Eva, args=(EA, EB, args))
    alice.start()
    bob.start()
    eva.start()
    alice.join()
    bob.join()
    eva.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Протокол порождения через нейросеть, симуляция Eva"
        )
    main(parser.parse_args())
