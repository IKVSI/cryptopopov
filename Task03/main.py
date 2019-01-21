#!/usr/bin/python3

import socket
import argparse
import random
import sys
from multiprocessing import Process, Pipe

#  --  Псевдоимена  --
names = [
    "Alice",
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

def log(name, mess):
    return name + (7-len(name))*" "+": "+mess

def client(name, pipes, messange):
    binmessange = ""
    if messange:
        messange = messange.encode("cp866")
        for i in messange:
            binmessange += "{:08b}".format(i)
        print(log(names[name], "Преобразовано сообщение к бинарному виду"))
        print(log(names[name], "M:{}".format(binmessange)))
    j = 0
    sym = 0
    M = ""
    while True:
        s = {}
        r = {}
        for i in pipes.keys():
            s[i] = random.randint(0, 1)
            pipes[i].send(s[i])
        for i in pipes.keys():
            r[i] = pipes[i].recv()
        for i in pipes.keys():
            r[i] ^= s[i]
        if messange:
            logtemp = "-- {} бит --".format(j)
            print(logtemp+(80-len(logtemp))*'-')
        logtemp = []
        temp = ""
        for i in pipes.keys():
            temp += "{}: {} ".format(i, r[i])
        logtemp.append(log(names[name], "Согласованы биты {}".format(temp)))
        ret = 0
        temp = ""
        for i in pipes.keys():
            ret ^= r[i]
            temp += "{}({})^".format(i[0], r[i])
        if messange:
            if (binmessange[j] == '1'):
                ret ^= 1
            temp += "M({})^".format(binmessange[j])
        logtemp.append(log(names[name], "Сгенерирован бит {} = {}".format(ret, temp[:-1])))
        for i in pipes.keys():
            pipes[i].send(ret)
        for i in pipes.keys():
            r[i] = pipes[i].recv()
        temp = "{}({})^".format(names[name][0], ret)
        for i in pipes.keys():
            ret ^= r[i]
            temp += "{}({})^".format(i[0], r[i])
        logtemp.append(log(names[name], "Получен анонимный бит {} = {}".format(ret, temp[:-1])))
        logtemp.append("")
        sym <<= 1
        sym += ret
        j += 1
        if not j%8:
            if sym == 0:
                break
            M += sym.to_bytes(1, "little").decode("cp866")
            sym = 0
        for k in range(0, name):
            pipes[names[k]].recv()
        print("\n".join(logtemp))
        for k in range(name+1, len(pipes)+1):
            pipes[names[k]].send(True)
    print(log(names[name], "Получено анонимное сообщение \"{}\"".format(M)))


def main(args):
    if (args.n < 3) or (args.n > 10):
        args.n = 3
    curent_names = names[:args.n]
    args.messange = " ".join(args.messange)
    pipes = []
    for i in range(args.n):
        pipes.append(dict())
    for i in range(args.n):
        for j in range(i+1, args.n):
            pipe1, pipe2 = Pipe(True)
            pipes[i][names[j]] = pipe1
            pipes[j][names[i]] = pipe2
    proc = []
    anonim = random.randint(0, args.n-1)
    print(log("Master", "{} был выбран анонимом для посылки сообщения".format(names[anonim])))
    for i in range(args.n):
        m = ""
        if i == anonim:
            m = args.messange+'\0'
        proc.append(Process(target=client, args=(i, pipes[i], m)))
    for i in range(args.n):
        proc[i].start()
    for i in range(args.n):
        proc[i].join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Программа реализации булевого протокола передачи анонимного сообщения"
        )
    parser.add_argument("-n", type=int, default=3, help="Количество людей в чате (от 3 до 10) default=3")
    parser.add_argument("messange", type=str, nargs="+", help="Сообщение для анонимной передачи")
    main(parser.parse_args())

# def f(conn):
#     conn.send([42, None, 'hello'])
#     conn.close()

# if __name__ == '__main__':
#     parent_conn, child_conn = Pipe()
#     p = Process(target=f, args=(child_conn,))
#     p.start()
#     print parent_conn.recv()   # prints "[42, None, 'hello']"
#     p.join()