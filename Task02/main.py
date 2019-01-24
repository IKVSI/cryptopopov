#!/usr/bin/python3

import argparse
import sys
import time
from Cryptodome import Random
import Cryptodome.Random.random as random
from Cryptodome.Cipher import AES
from multiprocessing import Process, Queue


NAME="MASTER"

def log(message):
    return NAME + (7-len(NAME))*" "+": "+message

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()

def hexit(i, ):
    t = hex(i)[2:]
    return t if len(t) == 2 else '0'+t

def Alice(bob, eva, args):
    global NAME
    NAME = "Alice"
    print(log("Генерируем {} сообщений шифруя {}-bit ключом".format(args.n, args.b)))
    blocks = []
    keys = []
    for i in range(args.n):
        key = Random.new().read(32)
        keys.append(key)
        M = "MESSAGE X={} KEY={}".format(i, key)
        M = M.encode("utf-8")
        M += (32 - len(M) % 32)*b'\0'
        blockkey = Random.new().read(args.b // 8)
        if args.b % 8:
            a = 0
            b = 1
            for j in range(args.b % 8):
                a ^= b
                b <<= 1
            blockkey += (Random.new().read(1)[0] & a).to_bytes(1, "little")
        blockkey += (32-len(blockkey))*b"\0"
        cipher = AES.new(blockkey, 1)
        blocks.append(cipher.encrypt(M))
    random.shuffle(blocks)
    print(log("Публикуем сгенерированные сообщения"))
    bob.put(blocks)
    eva.put(blocks)
    while not bob.empty():
        pass
    M = bob.get()
    print(log("Получено секретное сообщение от Боба с ключом номер {}\n  M: {}".format(*M)))
    cipher = AES.new(keys[M[0]], 1)
    M = cipher.decrypt(M[1])
    for i in range(len(M)-1, 0, -1):
        if M[i] != 0:
            break
    M = M[:i+1].decode("utf-8")
    print(log("M: {}".format(M)))

def hack(num, block, bit, start_time, sizemark):
    M = b''
    size = 2**bit-1
    sizeblock = []
    if sizemark:
        for i in range(1, sizemark):
            sizeblock.append(size // sizemark * i)
        sizeblock.append(size)
    k = 0
    for i in range(0, size):
        if i == sizeblock[k]:
            print(log("Обработано {} ключей для сообщения {} Прошло времени {:.3f} с".format(i, num, (time.time() - start_time))))
            k += 1
        blockkey = i.to_bytes(32, "little")
        cipher = AES.new(blockkey, 1)
        M = cipher.decrypt(block)
        if M[:7] == b'MESSAGE':
            break
    for i in range(len(M)-1, 0, -1):
        if M[i] != 0:
            break
    M = M[:i+1].decode("utf-8")
    temp = M.find("KEY=")
    X = int(M[10:temp])
    KEY = eval(M[temp+4:])
    return M, X, KEY

def Bob(alice, eva, args):
    global NAME
    NAME = "Bob"
    blocks = alice.get()
    print(log("Получены сообщения Алисы"))
    choice = random.randint(0, len(blocks)-1)
    if args.badday:
        choice = len(blocks)-1
    print(log("Выбрано сообщение {} для взлома".format(choice)))
    start_time = time.time()
    M, X, KEY = hack(choice, blocks[choice], args.b, start_time, args.status)
    print(log("Расшифрованно сообщение {}\n Затрачено времени: {:.3f} с".format(M, (time.time() - start_time))))
    cipher = AES.new(KEY, 1)
    Secret = b'Hello Alice'
    Secret += (32 - len(Secret) % 32)*b'\0'
    Secret = cipher.encrypt(Secret)
    print(log("Отправленно секретное сообщение для Alice c ключом номер {}".format(X)))
    alice.put((X, Secret))
    eva.put((X, Secret))

def Eva(alice, bob, args):
    global NAME
    NAME = "Eva"
    blocks = alice.get()
    print(log("Получены сообщения Алисы"))
    start_time = time.time()
    keys = dict()
    Xbob = -1
    Mbob = b''
    k = 0
    for block in blocks:
        M, X, KEY = hack(k, block, args.b, start_time, args.status)
        keys[X] = KEY
        k += 1
        if Xbob == -1:
            if bob.empty():
                continue
            else:
                Xbob, Mbob = bob.get()
        elif Xbob in keys.keys():
            break
    cipher = AES.new(keys[Xbob], 1)
    Mbob = cipher.decrypt(Mbob)
    for i in range(len(Mbob)-1, 0, -1):
        if Mbob[i] != 0:
            break
    Mbob = Mbob[:i+1].decode("utf-8")
    print(log("Секретное сообщение взломано ключом {}\n  M: {}\n Затрачено времени: {:.3f} с".format(Xbob, Mbob, (time.time() - start_time))))

def main(args):
    AB = Queue()
    AE = Queue()
    BE = Queue()
    alice = Process(target=Alice, args=(AB, AE, args))
    bob = Process(target=Bob, args=(AB, BE, args))
    eva = Process(target=Eva, args=(AE, BE, args))
    alice.start()
    bob.start()
    eva.start()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Реализация Головоломки Меркла на основе укорачивания ключа"
        )
    parser.add_argument("-n", type=int, help="Количество генерируемых сообщений")
    parser.add_argument("-b", type=int, help="Количество бит для ключа сообщений")
    parser.add_argument("-badday", action="store_true", help="Худший случай для Eva (Bob выбрал последее сообщение)")
    parser.add_argument("-status", type=int, default=0, help="Количество дополнительных временные отметок взлома")
    main(parser.parse_args())