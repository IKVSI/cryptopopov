usage: main.py [-h] [-s] [-port PORT] [-host HOST] [-prime PRIME]
               [-primeend PRIMEEND] [-p]
               [messange [messange ...]]

Программа для ознакомления с работой протокола Шамира

positional arguments:
  messange            Сообщения используют однобайтовую кодировку (default =
                      cp866)

optional arguments:
  -h, --help          show this help message and exit
  -s                  Запуск сервера Bob
  -port PORT          Порт для соединения или сервера
  -host HOST          Адрес подключения или сервера
  -prime PRIME        Установить своё простое число для сообщения
  -primeend PRIMEEND  Если установлено это число, то простое будет взято из
                      диапазона [prime, primeend]
  -p                  Пауза в конце программы
