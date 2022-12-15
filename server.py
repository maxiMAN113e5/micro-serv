#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from threading import Thread
import socket
import json
import pickle
import logging
import hashlib


class Server:
    def __init__(self, port):
        self.database = "./users.json"
        self.server_port = port
        self.users = []
        self.connections = []
        self.init_server()

    def init_server(self):
        # Инициализация сервера
        sock = socket.socket()
        sock.bind(('', self.server_port))
        sock.listen(5)
        self.sock = sock
        logging.info(f"Старт сервера, порт: {self.server_port}")
        while True:
            conn, addr = self.sock.accept()
            Thread(target=self.client_logic, args=(conn, addr)).start()
            logging.info(f"Подключение клиента {addr}")
            self.connections.append(conn)

    def broadcast(self, msg, conn, username):
        # Отправка сообщений всем клиентам (чат)
        for connection in self.connections:
            if connection != conn:
                connection.send(pickle.dumps(["message", msg, username]))
                logging.info(f"Отправка данных клиенту {connection.getsockname()}: {msg}")

    def client_logic(self, conn, address):
        # Поток прослушивания клиентов
        self.authorization(address, conn)
        while True:
            try:
                data = conn.recv(1024)
            except ConnectionResetError:
                conn.close()
                self.connections.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break
            if data:
                status, data, username = pickle.loads(data)
                logging.info(f"Прием данных от клиента '{username}_{address[1]}': {data}")
                if status == "message":
                    self.broadcast(data, conn, username)
                elif status == "shutdown":
                    for connection in self.connections:
                        connection.send(pickle.dumps(["message", f"{username} выключил сервер", "~SERVER~"]))
                        connection.close()
                    logging.info(f"Отключение сервера по команде")
                    self.sock.close()
                    break
                elif status == "exit":
                    logging.info(f"Закрытие соединения с клиентом {username}")
                    conn.close()
                    self.connections.remove(conn)
                    for connection in self.connections:
                        connection.send(pickle.dumps(["message", f"{username} отключился от сервера", "~SERVER~"]))
                    break
            else:
                # Закрываем соединение
                conn.close()
                self.connections.remove(conn)
                logging.info(f"Отключение клиента {address}")
                break

    def authorization(self, addr, conn):
        # Авторизация пользователей
        conn.send(pickle.dumps(["auth", "Введите имя пользователя: "]))
        username = pickle.loads(conn.recv(1024))[1]
        try:
            # Данные пользователей из файла
            self.users = self.database_read()
        except json.decoder.JSONDecodeError:
            # Первичная запись в пустой файл
            self.registration(addr, conn, username)
        is_registered = False
        for user in self.users:
            for key, value in user.items():
                if key == username:
                    is_registered = True
                    password = value['password']
                    conn.send(pickle.dumps(["passwd", "Введите свой пароль: "]))
                    passwd = pickle.loads(conn.recv(1024))[1]
                    # Проверка пароля
                    if self.check_password(passwd, password):
                        conn.send(pickle.dumps(["success", f"Добро пожаловать, {username}"]))
                    else:
                        # Если пароль неверный снова отправляем на авторизацию
                        self.authorization(addr, conn)
                    logging.info(f"Клиент {self.sock.getsockname()} успешно авторизировался")
        if not is_registered:
            self.registration(addr, conn, username)

    def registration(self, addr, conn, username):
        # Регистрация пользователя с новым username
        conn.send(pickle.dumps(["passwd", "Введите новый пароль: "]))
        passwd = self.generate_hash(pickle.loads(conn.recv(1024))[1])
        conn.send(pickle.dumps(["success", f"Успешная регистрация, {username}"]))
        self.users.append({username: {'password': passwd, 'address': addr[0]}})
        # Запись в файл при регистрации пользователя
        logging.info(f"Клиент {self.sock.getsockname()} успешно зарегистрировался")
        self.database_write()
        self.users = self.database_read()

    def database_read(self):
        with open(self.database, 'r') as f:
            users = json.load(f)
        return users

    def database_write(self):
        with open(self.database, 'w') as f:
            json.dump(self.users, f, indent=4)

    def check_password(self, user_input, real_password):
        # Проверка пароля
        key = hashlib.md5(user_input.encode() + b'salt').hexdigest()
        correct_password = key == real_password
        return correct_password

    def generate_hash(self, passwd):
        # Генерация хеша для безопасного хранение паролей
        key = hashlib.md5(passwd.encode() + b'salt').hexdigest()
        return key


def is_available_port(port):
    try:
        sock = socket.socket()
        sock.bind(("", port))
        sock.close()
        logging.info(f"Порт {port} свободен")
        return True
    except OSError:
        logging.info(f"Порт {port} занят")
        return False


logging.basicConfig(format="%(asctime)s [%(levelname)s] %(funcName)s: %(message)s",
                    handlers=[logging.FileHandler("logs/server.log"), logging.StreamHandler()], level=logging.INFO)


def main():
    server_port = 9090  # порт по умолчанию
    # Если порт по умолчанию занят, то перебираем порты
    if not is_available_port(server_port):
        logging.info(f"Порт по умолчанию {server_port} занят")
        port_available = False
        while not port_available:
            server_port += 1
            port_available = is_available_port(server_port)
    Server(server_port)


if __name__ == "__main__":
    main()

