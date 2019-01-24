#!/usr/bin/python3

import argparse
import json
import datetime
import sys
import Cryptodome.Random.random as random
from Cryptodome.Hash import SHA1
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import pss as PSS
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

def log(message):
    return NAME + (7-len(NAME))*" "+": "+message

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()

#  --  Генерация ID  --
def generateID():
    ID = ""
    for i in range(16):
        t = hex(random.randint(0,255))[2:]
        ID += t if len(t) == 2 else '0'+t
    return ID

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
        self.data = {"amount": amount, "ID": generateID()}
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
        self.datahash = SHA1.new(self.data).hexdigest()

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
    
    def __str__(self):
        ln = 55
        if type(self.data) is bytes:
            amount = None
            ID = None
        else:
            amount = self.data["amount"]
            ID = self.data["ID"]
        temp = [" "+"-"*ln+" "]
        t = "|  Check  ID : {}".format(ID)
        temp.append(t + (ln+1 - len(t)) * " " + "|")
        t = "|  Amount    : {} $".format(amount)
        temp.append(t + (ln+1 - len(t)) * " " + "|")
        t = "|  Data hash : {}".format(self.datahash)
        temp.append(t + (ln+1 - len(t)) * " " + "|")
        t = "|  Date/Time : {}".format(self.date)
        temp.append(t + (ln+1 - len(t)) * " " + "|")
        if self.signature:
            signature = ""
            for i in self.signature:
                t = hex(i)[2:]
                signature += t if len(t) == 2 else '0'+t
            i = 0
            t = "|  Signature : {}"
            while i < len(signature):
                if (i + len(self.datahash)) < len(signature):
                    t = t.format(signature[i:i+len(self.datahash)])
                    temp.append(t + (ln+1 - len(t)) * " " + "|")
                    t = "|              {}"
                else:
                    t = t.format(signature[i:])
                    temp.append(t + (ln+1 - len(t)) * " " + "|")
                i += len(self.datahash)
        else:
            t = "|  Signature : {}"
            t = t.format(self.signature)
            temp.append(t + (ln+1 - len(t)) * " " + "|")
        temp.append(" "+"-"*ln+" ")
        temp.append("")
        return "\n".join(temp)


def Alice(sellerpipe, bankpipe, PUBLIC_BANK_KEY, args):
    global NAME
    count = args.count
    NAME = "Alice"
    print(log("Генерируем чеки в количесве {} штук".format(count)))
    checks = []
    gamma = []
    t = random.randint(0, count-1)
    if not args.amount:
        args.amount = AMOUNT
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
            sellerpipe.send(-1)
            return
        print(log("Получен номер {} чека для проверки суммы".format(check+1)))
        bankpipe.send(gamma[check])
        check = bankpipe.recv()
    choice = bankpipe.recv()
    print(log("Получен чек подписанный банком"))
    check.decode(gamma[choice])
    print(log("Расшифровываем конверт"))
    check.open()
    print(check)
    if args.fakedata:
        check.data["amount"] = 100
        print(log("Меняем сумму в чеке и пробуем отдать продавцу"))
        sellerpipe.send(check)
        return
    if args.fakesign:
        ch = Check(100)
        ch.sign(check.signature, check.date)
        ch.open()
        print(log("Генерируем поддельный чек с полученной подписью банка"))
        sellerpipe.send(ch)
        return
    print(log("Отправляем чек продавцу"))
    sellerpipe.send(check)

def Seller(alicepipe, bankpipe, PUBLIC_BANK_KEY, args):
    global NAME
    NAME = random.choice(NAMES)
    check = alicepipe.recv()
    if type(check) is int:
        print(log("Чек не получен"))
        return
    print(log("Получен чек"))
    try:
        datahash = SHA1.new(json.dumps(check.data).encode("utf-8")).hexdigest()
        print("Проверяем целостость данных\n  datahash       : {}\n  check.datahash : {}".format(datahash, check.datahash))
        if datahash != check.datahash:
            print(log("Чек поддельный!!! Изменены данные!"))
            return
        print(log("Проверяем подпись банка"))
        PSS.new(RSA.import_key(PUBLIC_BANK_KEY)).verify(SHA1.new((check.datahash + check.date).encode("utf-8")), check.signature)
        print(log("Подпись проверена открытым ключом Банка, чек корректный"))
    except ValueError as ex:
        print(log("Чек поддельный!!! {}".format(ex)))

def Bank(alicepipe, sellerpipe, PRIVATE_BANK_KEY, PUBLIC_BANK_KEY, args):
    global NAME
    NAME = "Bank"
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
    date = '{0:%Y-%m-%d %H:%M}'.format(datetime.datetime.now())
    check.sign(PSS.new(RSA.import_key(PRIVATE_BANK_KEY)).sign(SHA1.new((check.datahash+date).encode("utf-8"))), date)
    print(log("Чек номер {} подписан банком и отправлен\n{}".format(choice+1, check)), end="")
    print("-"*60)
    alicepipe.send(check)
    alicepipe.send(choice)

def main(args):
    print(log("Генерируем ключи RSA Банка для подписи"))
    PRIVATE_BANK_KEY = RSA.generate(1024)
    PUBLIC_BANK_KEY = PRIVATE_BANK_KEY.publickey().export_key()
    PRIVATE_BANK_KEY = PRIVATE_BANK_KEY.export_key()
    alicesellerpipe, selleralicepipe = Pipe(True)
    banksellerpipe, sellerbankpipe = Pipe(True)
    alicebankpipe, bankalicepipe = Pipe(True)
    alice = Process(target=Alice, args=(alicesellerpipe, alicebankpipe, PUBLIC_BANK_KEY, args))
    seller = Process(target=Seller, args=(selleralicepipe, sellerbankpipe, PUBLIC_BANK_KEY, args))
    bank = Process(target=Bank, args=(bankalicepipe, banksellerpipe, PRIVATE_BANK_KEY, PUBLIC_BANK_KEY, args))
    alice.start()
    bank.start()
    seller.start()
    alice.join()
    seller.join()
    bank.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Программа подписи чека в банке с анонимным ID конверты"
        )
    parser.add_argument("count", type=int, help="Количество чеков для отправки банку (Степень доверия)")
    parser.add_argument("-amount", type=int, help="Запуск программы с попыткой подделать 1 чек другой суммой (в чеках сумма {})".format(AMOUNT))
    parser.add_argument("-fakesign", action='store_true', help="Пробуем подставить подпись в другой чек")
    parser.add_argument("-fakedata", action='store_true', help="Пробуем подставить другие данные в чек")
    main(parser.parse_args())