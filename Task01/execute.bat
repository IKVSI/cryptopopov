@ECHO OFF
TITLE BOB
START /B python main.py -s -p
START "ALICE" python main.py Секретное сообщение -prime 16769023 -p
