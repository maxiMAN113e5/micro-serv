#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from threading import Thread
from getpass import getpass
import socket
import sys
import logging
import pickle
import time


class Client:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        # состояние для обработки входящих пакетов
        self.server_connection()
        self.server_sync()

    def server_connection(self):
        # Соединение с сервером
        sock = socket.socket()
        try:
            sock.connect((self.server_ip, self.server_port))
        except ConnectionRefusedError:
            print(f"Не удалось присоединиться к серверу {self.server_ip, self.server_port}")
            sys.exit(0)
        self.sock = sock
        print(f"Установлено соединение с сервером ('{self.server_ip}', {self.server_port})")
        logging.info(
            f"Установлено соединение {self.sock.getsockname()} с сервером ('{self.server_ip}', {self.server_port})")

    def server_sync(self):
        # Вызов функций при получении команд (статусов) от сервера
        Thread(target=self.receive_data).start()
        print("'exit' - разорвать соединение, 'shutdown' - выключить сервер")
        self.status = None
        while True:
            if self.status:
                if self.status == "auth":
                    self.auth()
                elif self.status == "register":
                    self.register()
                    logging.info(f"Пользователь {self.sock.getsockname()} успешно зарегистрировался")
                elif self.status == "passwd":
                    self.send_passwd()
                elif self.status == "success":
                    self.success()
                else:
                    user_input = input(f"{self.username}> ")
                    if user_input != "":
                        if user_input == "exit":
                            print(f"Разрыв соединения {self.sock.getsockname()} с сервером по команде")
                            logging.info(f"Разрыв соединения {self.sock.getsockname()} с сервером по команде")
                            close_connection = pickle.dumps(["exit", "Разрыв соедиенения", self.username])
                            self.sock.send(close_connection)
                            self.sock.close()
                            sys.exit(0)
                        elif user_input == "shutdown":
                            shutdown_server = pickle.dumps(["shutdown", "Отключение сервера", self.username])
                            self.sock.send(shutdown_server)
                        # Отправляем сообщение и имя клиента
                        send_message = pickle.dumps(["message", user_input, self.username])
                        self.sock.send(send_message)
                        logging.info(f"Отправка данных от {self.sock.getsockname()} на сервер: {user_input}")

    def receive_data(self):
        # Поток получения и обработки данных от сервера
        # Клиент принимает пакет вида ["status", "message"]
        while True:
            try:
                self.data = self.sock.recv(1024)
                if not self.data:
                    sys.exit(0)
                self.status = pickle.loads(self.data)[0]
                # Вывод сообщений от других пользователей
                if self.status == "message":
                    print(f"\n{pickle.loads(self.data)[2]}->", pickle.loads(self.data)[1])
                    logging.info(f"{self.sock.getsockname()} получил данные от сервера: {pickle.loads(self.data)[1]}")
                else:
                    self.data = pickle.loads(self.data)[1]
            except OSError:
                break

    def send_passwd(self):
        # Отправка пароля на сервер
        passwd = getpass(self.data)
        self.sock.send(pickle.dumps(["passwd", passwd]))
        time.sleep(0.25)

    def auth(self):
        self.username = input("Введите имя пользователя: ")
        self.sock.send(pickle.dumps(["auth", self.username]))
        time.sleep(0.25)

    def register(self):
        self.username = input("Введите новое имя пользователя: ")
        self.sock.send(pickle.dumps(["register", self.username]))
        time.sleep(0.25)

    def success(self):
        # Вывод сообщения об успешной регистрации или авторизации
        print(self.data)
        self.status = "ready"
        self.username = self.data.split(" ")[2]
        logging.info(f"Клиент {self.sock.getsockname()} прошел авторизацию")


def ip_validation(ip):
    if ip == "":
        return False
    else:
        try:
            octets = ip.split(".", 4)
            if len(octets) == 4:
                for octet in octets:
                    octet = int(octet)
                    if 0 <= octet <= 255:
                        pass
                    else:
                        return False
            else:
                return False
        except ValueError:
            return False
        return True


def port_validation(port):
    try:
        value = int(port)
        if 1 <= value <= 65535:
            return True
        print(f"Неправильное значение - {value} для порта")
        return False
    except ValueError:
        print(f"{port} - не число")
        return False

def main():
    user_port = input("Введите порт сервера (enter для значения по умолчанию):")
    user_ip = input("Введите IP-адрес сервера (enter для значения по умолчанию):")
    # Валидация порта и IP адреса клиента
    if not port_validation(user_port):
        user_port = 9090
        print(f"Установлен порт {user_port} по умолчанию")
    if not ip_validation(user_ip):
        user_ip = "127.0.0.1"
        print(f"Установлен IP-адрес {user_ip} по умолчанию")
    Client(user_ip, int(user_port))


if __name__ == "__main__":
    main()


# In[ ]:




