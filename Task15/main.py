#!/usr/bin/python3

import argparse
import sys
from multiprocessing import Process, Pipe
from sympy import sieve
from sympy.ntheory import factorint
from sympy.ntheory.residue_ntheory import nthroot_mod
import Cryptodome.Random.random as random

NAME="MASTER"

def log(message):
    return NAME + (7-len(NAME))*" "+": "+message

#  --  Переинициализация команды print для multiprocessing --
def print(text, end='\n'):
    sys.stdout.write(str(text)+'\n')
    sys.stdout.flush()

def reverse(q, prime):
    x2, x1, y2, y1 = 1, 0, 0, 1
    p = prime
    while q > 0:
        z, r = divmod(p, q)
        x = x2 - z * x1
        y = y2 - z * y1
        p = q
        q = r
        x2 = x1
        x1 = x
        y2 = y1
        y1 = y
    return y2 % prime

def Alice(bob, args):
    global NAME
    NAME = "Alice"
    primes = [ i for i in sieve.primerange(1000, 5000)]
    prime = random.choice(primes)
    factor = factorint(prime - 1)
    fl = True
    X = None
    while fl:
        X = random.choice([ i for i in range(3, prime-2, 2) ] )
        fl = False
        for i in factor.keys():
            if not X % i:
                fl = True
    A = random.randint(2, prime-2)
    C = pow(A, X, prime)
    print(log("Нужно доказать Бобу, что знаю X для решения уравнения"))
    print(log("{} ^ X = {} (mod {})".format( A, C, prime)))
    bob.send((A, C, prime))
    print(log("Генерируем {} значений Ri < Prime-1 (столько нужно чтобы убедить Боба)".format(args.n)))
    R = [random.randint(2, prime-2) for i in range(args.n)]
    print(log("Вычисляем Hi = {} ^ Ri (mod {}) и посылаем Бобу".format(A, prime)))
    H = [ pow(A, i, prime) for i in R ]
    bob.send(H)
    print(log("Используя протокол бросания монетки генерируем {} битов".format(args.n)))
    #  --  Бросание монетки с помощью корней  --
    qprime = prime
    while qprime == prime:
        qprime = random.choice(primes)
    pprime = qprime
    while pprime == prime or qprime == pprime:
        pprime = random.choice(primes)
    N = pprime * qprime
    print(log("Посылаем бобу {}(N) = {}(p) * {}(q)".format(N, pprime, qprime)))
    bob.send(N)
    Z = bob.recv()
    roots = []
    rb = []
    for i in Z:
        root = nthroot_mod(i, 2, N, True)
        root.sort()
        roots.append(root[:2])
        rb.append(random.choice(roots[-1]))
    print(log("Пытаемся угадать вычеты и отправляем Бобу"))
    bob.send(rb)
    B = bob.recv()
    print(log("Получены биты B: {}".format(B)))
    r = bob.recv()
    print(log("Получены корни боба r"))
    Btemp = []
    K = -1
    for i in range(args.n):
        if (r[i] == rb[i]) and B[i]:
            if K < 0:
                K = i
            Btemp.append(1)
        elif (r[i] in roots[i]) and (not B[i]):
            Btemp.append(0)
        else:
            Btemp.append(-1)
    print(log("Биты по r Боба: {}".format(Btemp)))
    if -1 in Btemp:
        print(log("Что-то пошло не так !!!"))
        bob.send(-1)
        return
    else:
        bob.send(0)
    print(log("Генерируем сообщение M если Bi=0 то Ri, если Bi=1 то Ri-R{} mod (prime-1)".format(K)))
    M = [(R[i]-R[K])%(prime-1) if B[i] else R[i] for i in range(args.n)]
    bob.send(M)
    print(log("Также посылаем Бобу X-R{} (mod prime-1)".format(K)))
    bob.send((X-R[K]) % (prime-1))

def Bob(alice, args):
    global NAME
    NAME = "Bob"
    A, C, prime = alice.recv()
    H = alice.recv()
    print(log("Получены Hi"))
    B = []
    N = alice.recv()
    r = set()
    while len(r) != args.n:
        r.add(random.randint(2, N//2))
    r = list(r)
    random.shuffle(r)
    r = r[:20]
    Z = [pow(i, 2, N) for i in r]
    print(log("Сгенерировано {} Z=r^2 (mod N) квадратичных вычетов".format(args.n)))
    alice.send(Z)
    rb = alice.recv()
    B = [ 1 if rb[i] == r[i] else 0 for i in range(args.n) ]
    K = -1
    for i in range(args.n):
        if B[i]:
            K=i
            break
    print(log("На основе ответов Алисы сгенерированы биты B"))
    alice.send(B)
    alice.send(r)
    if alice.recv():
        return
    M = alice.recv()
    print(log("Начинаем проверку утверждений"))
    print(log("если Bi = 0, то A^Mi = Hi (mod prime)"))
    print(log("если Bi = 1, то A^Mi = Hi*Hj^-1 (mod prime)"))
    ANS = []
    for i in range(args.n):
        if B[i]:
            ANS.append( pow(A, M[i], prime) == ((H[i]*reverse(H[K], prime))%prime) )
        else:
            ANS.append( pow(A, M[i], prime) == (H[i]%prime) )
    print(log("ANS: {}".format(ANS)))
    Z = alice.recv()
    FINAL = (pow(A, Z, prime) == (C*reverse(H[K], prime))%prime)
    if False not in ANS and FINAL:
        print(log("FINAL={} Я уверен что Алиса знает X с вероятностью {:03f}".format(FINAL, 1-1/(2**args.n))))


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
        description="Реализация протокола доказательства с нулевым разглашением на основе дискретного логорифма"
        )
    parser.add_argument("-n", type=int, default=15, help="Количество проверок для убеждения Боба, default=15")
    main(parser.parse_args())
