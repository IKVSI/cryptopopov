#!/usr/bin/python3

import argparse
import random
from sympy import sieve

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

def printmatrix(matrix, vector):
    temp="\t|\t"
    for j in range(len(vector)):
        temp += "{}\t".format(j)
    temp += "|\tV\n"
    temp += "-"*60+"\n"
    for i in range(len(vector)):
        temp += "{}\t|\t".format(i)
        for j in range(len(vector)):
            temp += "{}\t".format(matrix[i][j])
        temp += "|\t{}\n".format(vector[i])
    print(temp)


def answer(matrix, vector, prime):
    for i in range(len(vector)):
        t = reverse(matrix[i][i], prime)
        for j in range(len(vector)):
            matrix[i][j] = (matrix[i][j] * t) % prime
        vector[i] = (vector[i] * t) % prime
        for k in range(len(vector)):
            if k == i:
                continue
            t2 = matrix[k][i]
            for j in range(len(matrix)):
                matrix[k][j] = (matrix[k][j] - t2 * matrix[i][j]) % prime
            vector[k] = (vector[k] - vector[i] * t2) % prime
        #printmatrix(matrix, vector)
    return vector

def restore(files):
    files = list(set(files))
    secretparts = []
    size = len(files)
    print("Предоставлено {} секретных частей".format(size))
    for i in files:
        fin = open(i, "r")
        part = []
        for j in fin:
            part.append(tuple(int(k) for k in j.split()))
        fin.close()
        secretparts.append(part)
    for i in range(1, len(secretparts)):
        if len(secretparts[i-1]) != len(secretparts[i]):
            raise ValueError("Different Secrets!")
    secret = ""
    for i in range(len(secretparts[0])):
        matrix = []
        vector = []
        for j in range(size):
            vector.append(0)
            matrix.append([0 for k in range(size)])
        prime = secretparts[0][i][2]
        for j in range(len(secretparts)):
            x = secretparts[j][i][0]
            v = secretparts[j][i][1]
            xtemp = 1
            for k in range(size-1, -1, -1):
                matrix[j][k] = xtemp
                xtemp = (xtemp * x) % prime
            vector[j] = v
        #printmatrix(matrix, vector)
        answer(matrix, vector, prime)
        #printmatrix(matrix, vector)
        sym = vector[-1]
        if sym > 255:
            raise ValueError("Ошибка декодирования, не хватает частей секрета")
        secret += sym.to_bytes(1, "little").decode("cp866")
    print("Secret: {}\n".format(secret))
    

def main(args):
    if args.restore:
        restore(args.restore)
        return
    args.secret = " ".join(args.secret)
    #  --  Разбиваем секрет на числовые блоки  --
    numsecret = [ int.from_bytes(i.encode("cp866"), "little") for i in args.secret ]
    secretparts = []
    for i in range(args.parts):
        secretparts.append([])
    #  --  Для каждого блока создаём набор разделений  --
    for i in numsecret:
        # Выбираем простое число > 1 байта
        prime = random.choice([j for j in sieve.primerange(500, 1000)])
        a = [i]
        # Выбираем набор коэфициентов
        for j in range(args.access-1):
            a.append(random.randint(1, prime-1))
        # Выбираем коэфициент для разделения
        xarr = [j for j in range(1, prime-1)]
        for j in range(args.parts):
            x = random.choice(xarr)
            xarr.remove(x)
            v = 0
            xtemp = 1
            for k in range(args.access):
                v = (v + a[k]*xtemp) % prime
                xtemp = xtemp*x % prime
            # Записываем разделение блока
            secretparts[j].append((x, v, prime))
    # Записываем разделение в файл
    for i in range(args.parts):
        fname = "secret-{}.seq".format(i+1)
        fout = open(fname, "w")
        for i in secretparts[i]:
            fout.write("{} {} {}\n".format(*i))
        fout.close()
        print("Записан файл {} c частью секрета".format(fname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Программа реализации разделения секрета с помощью многочленов Лагранжа"
        )
    parser.add_argument("-restore", type=str, nargs="+", help="Путь к файлам с разделёнными секретами")
    parser.add_argument("-access", type=int, default=3, help="Количество человек для доступа к секрету")
    parser.add_argument("-parts", type=int, default=5, help="Количество разделений секрета")
    parser.add_argument("secret", type=str, nargs="*", help="Секрет")
    main(parser.parse_args())
