@ECHO OFF
TITLE BOB
START /B python main.py -s -p
START "ALICE" python main.py Hello my friend! -prime 100000 -primeend 1000000 -p