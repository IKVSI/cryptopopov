@ECHO OFF
TITLE BOB
START /B python main.py -s
START "ALICE" python main.py Hello my friend! -prime 100000 -primeend 1000000