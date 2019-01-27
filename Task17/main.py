#!/usr/bin/python3

import argparse
import sys
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
        #prntmsg(ciphertext, "EMSG: ")
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


def Alice(bob, KEY, args):
    global NAME
    NAME = "Alice"
    net = NeuralNet(KEY)
    MESS =  [ i for i in range(256) ]
    random.shuffle(MESS)
    MESS = bytes(MESS)
    print(log("Отправляем зашифрованное сетью секретное сообщение"))
    DMESS = net.encrypt(MESS)
    bob.send(DMESS)
    while True:
        DMESS = bob.recv()
        positions = NeuralNet.analise(MESS, DMESS)
        bob.send(positions)
        if False not in positions:
            break
    bob.recv()
    print(log("Все биты совпали, сеть готова для шифрования"))

def Bob(alice, KEY, args):
    global NAME
    NAME = "Bob"
    net = NeuralNet(KEY)
    EMESS = alice.recv()
    rnd = 1
    while True:
        DMESS = net.decrypt(EMESS)
        print(log("{} раунд: Декодируем сообщение и отправляем Alice для проверки".format(rnd)))
        alice.send(DMESS)
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
        net.reinforce(positions)
        rnd += 1
    alice.send(1)


def main(args):
    AB, BA = Pipe(True)
    KEY = random.randint(1,254)
    alice = Process(target=Alice, args=(AB, KEY, args))
    bob = Process(target=Bob, args=(BA, KEY, args))
    alice.start()
    bob.start()
    alice.join()
    bob.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Протокол обучения нейросетевого криптографического шифра"
        )
    main(parser.parse_args())
