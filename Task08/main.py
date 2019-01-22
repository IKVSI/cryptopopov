#!/usr/bin/python3

import argparse
import random
import json
import datetime
import hashlib
import sys

from multiprocessing import Process, Pipe
NAME="MASTER"
AMOUNT = 1000
NAMES = [
    "Bob",
    "Charlie",
    "Dina",
    "Eva",
    "Feona",
    "George",
    "Helen",
    "Ivan",
    "Julia"
]

def log(messange):
    return NAME + (7-len(NAME))*" "+": "+messange

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()

def encode(data, gamma=b''):
    fl = True if gamma else False
    rdata = b''
    for i in range(len(data)):
        if fl:
            g = gamma[i]
        else:
            g = random.randint(1, 254)
            gamma += g.to_bytes(1, "little")
        rdata += (data[i]^g).to_bytes(1, "little")
    return(rdata, gamma)

class Check():
    
    def __init__(self, amount):
        self.data = {"amount": amount, "ID": random.randint(1, 65535)}
        self.date = None
        self.signature = None
        self.close()
    
    def encode(self):
        self.data, gamma = encode(self.data)
        return gamma

    def decode(self, gamma):
        self.data, _ = encode(self.data, gamma)

    def close(self):
        self.data = json.dumps(self.data).encode("utf-8")

    def open(self):
        dt = None
        if (type(self.data) is dict):
            print(log("Конверт уже открыт"))
            return 1
        try:
            dt = json.loads(self.data.decode("utf-8"))
        except UnicodeDecodeError:
            pass
        if (type(dt) is dict) and ("amount" in dt.keys()) and ("ID" in dt.keys()):
            self.data = dt
            print(log("Конверт открыт"))
            return 1
        print(log("Конверт не может быть открыт, он зашифрован"))
        return 0
    
    def sign(self, signature, date):
        self.date = date
        self.signature = signature
        return self.encode()
    
    def __str__(self):
        if type(self.data) is bytes:
            amount = None
            ID = None
        else:
            amount = self.data["amount"]
            ID = self.data["ID"]
        temp = [" "+"-"*50+" "]
        t = "|  Check  ID : {}".format(ID)
        temp.append(t + (51 - len(t)) * " " + "|")
        t = "|  Amount    : {} $".format(amount)
        temp.append(t + (51 - len(t)) * " " + "|")
        if type(self.data) is bytes :
            t = "|  Data hash : {}".format(hashlib.md5(self.data).hexdigest())
            temp.append(t + (51 - len(t)) * " " + "|")
        else:
            dt = json.dumps(self.data).encode("utf-8")
            t = "|  Data hash : {}".format(hashlib.md5(dt).hexdigest())
            temp.append(t + (51 - len(t)) * " " + "|")
        t = "|  Date/Time : {}".format(self.date)
        temp.append(t + (51 - len(t)) * " " + "|")
        t = "|  Signature : {}".format(self.signature)
        temp.append(t + (51 - len(t)) * " " + "|")
        temp.append(" "+"-"*51+" ")
        temp.append("")
        return "\n".join(temp)


def Alice(count, clientpipe, bankpipe, args):
    global NAME
    NAME = "Alice"
    print(log("Генерируем чеки в количесве {} штук".format(count)))
    checks = []
    gamma = []
    if args.amount != AMOUNT:
        t = random.randint(0, count-1)
    for i in range(count):
        if t == i:
            checks.append(Check(args.amount))
        else:
            checks.append(Check(AMOUNT))
        gamma.append(checks[i].encode())
    print(log("Отправляем чеки"))
    bankpipe.send(checks)
    check = bankpipe.recv()
    while type(check) is int:
        if check == -1:
            print(log("Банк отказался подписывать чеки"))
            clientpipe.send(-1)
            return
        print(log("Получен номер {} чека для проверки суммы".format(check+1)))
        bankpipe.send(gamma[check])
        check = bankpipe.recv()
    choice = bankpipe.recv()
    print(log("Получен чек подписанный банком"))
    check.decode(gamma[choice])
    print(log("Конверт декодирован моей гамма\n{}".format(check)+"-"*60))
    check.open()
    print(log("Отправляем декодированный чек продавцу"))
    clientpipe.send(check)

def Client(alicepipe, bankpipe, args):
    global NAME
    NAME = random.choice(NAMES)
    check = alicepipe.recv()
    if type(check) is int:
        print(log("Чек не получен"))
        return
    print(log("Получен чек"))
    print(log("Пробуем обналичить чек в банке"))
    bankpipe.send(check)
    money = bankpipe.recv()
    if money < 0:
        print(log("Чек не прошёл проверку, отказ обналичить"))
    else:
        print(log("Чек подтверждён, получено {} $".format(money)))

def Bank(count, alicepipe, clientpipe, args):
    global NAME
    NAME = "Bank"
    checks = dict()
    alicechecks = alicepipe.recv()
    print(log("Получено {} чеков".format(len(alicechecks))))
    choice = random.randint(0, len(alicechecks)-1)
    print(log("Выбираем чек номер {} (после проверки остальных будет подписан)".format(choice+1)))
    alicechecks[choice].open()
    amount = -1
    print("-"*60)
    for i in range(len(alicechecks)):
        if i == choice:
            continue
        alicepipe.send(i)
        gamma = alicepipe.recv()
        print(log("Получена гамма для чека номер {}".format(i+1)))
        alicechecks[i].decode(gamma)
        alicechecks[i].open()
        #  --  Проверка суммы в чеке  --
        if (amount == -1) or (amount == alicechecks[i].data["amount"]):
            amount = alicechecks[i].data["amount"]
            print(log("Чек проверен\n{}".format(alicechecks[i])))
            print("-"*60)
        else:
            print(log("В чеке неправильная сумма\n{}".format(alicechecks[i])))
            alicepipe.send(-1)
            return
    check = alicechecks[choice]
    signature = hashlib.md5(("BANK"+str(datetime.datetime.now())).encode("utf-8")).hexdigest()
    checks[signature] = check.sign(signature, '{0:%Y-%m-%d %H:%M}'.format(datetime.datetime.now()))
    print(log("Чек номер {} подписан банком, зашифрован и отправлен\n{}".format(choice+1, check)), end="")
    print("-"*60)
    alicepipe.send(check)
    alicepipe.send(choice)
    check = clientpipe.recv()
    print(log("Получен чек на проверку"))
    if check.signature in checks.keys():
        print(log("Сигнатура чека найдена в базе"))
        print(log("Пробуем декодировать и открыть конверт"))
        check.decode(checks[check.signature])
        if check.open():
            print(check)
            print(log("Чек подтверждён и обналичено {} $".format(check.data["amount"])))
            clientpipe.send(check.data["amount"])
        else:
            clientpipe.send(-1)
    else:
        print(log("Не найден чек в базе"))
        clientpipe.send(-1)

def main(args):
    aliceclientpipe, clientalicepipe = Pipe(True)
    bankclientpipe, clientbankpipe = Pipe(True)
    alicebankpipe, bankalicepipe = Pipe(True)
    alice = Process(target=Alice, args=(args.count, aliceclientpipe, alicebankpipe, args))
    client = Process(target=Client, args=(clientalicepipe, clientbankpipe, args))
    bank = Process(target=Bank, args=(args.count, bankalicepipe, bankclientpipe, args))
    alice.start()
    bank.start()
    client.start()
    alice.join()
    client.join()
    bank.join()




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Программа подписи чека в банке с анонимным ID конверты"
        )
    parser.add_argument("count", type=int, help="Количество чеков для отправки банку (Степень доверия)")
    parser.add_argument("-amount", type=int, help="Запуск программы с попыткой подделать 1 чек другой суммой (в чеках сумма {})".format(AMOUNT))
    main(parser.parse_args())