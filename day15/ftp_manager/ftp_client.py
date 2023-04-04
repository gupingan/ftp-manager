import time
import sys
from threading import Thread, Event
from socket import *


class ProgressBar:
    def __init__(self, current: int, target: int, tag: str = "#", count: int = 100):
        self.current = current
        self.target = target
        self.tag = tag
        self.count = count
        self.loaded = False

    def update(self, value):
        self.current += value

    def finished(self) -> bool:
        if self.loaded:
            return self.current >= self.target
        return self.loaded

    def listen(self):
        part = self.target // self.count + 1
        print("[", end="")
        finished = 0
        while True:
            # print(part, self.current, finished)
            if finished >= self.count:
                break
            time.sleep(0.01)
            if self.current >= part * (finished + 1):
                print("#", end="")
                finished += 1
        print("]", end="\n")
        self.loaded = True

    def run(self):
        thread = Thread(target=self.listen)
        thread.start()


class FTPClient:
    def __init__(self, host: str = "", port: int = 8888):
        self.host, self.port = host, port
        self.server_addr = (self.host, self.port)
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.download_file = None
        self.event = Event()

    def __connect(self):
        print("FTP:建立连接中......")
        self.sock.connect(self.server_addr)
        print("FTP:连接成功")

    def __stop(self):
        self.sock.close()
        sys.exit("FTP:客户端已经断开连接")

    def run(self):
        self.__connect()
        self.event.set()
        while True:
            current = self.sock.recv(1024 * 1024)
            cmd = input(f"{current.decode()} > ")
            if not cmd:
                continue
            self.sock.send(cmd.encode())
            if cmd in ("quit", "exit"):
                break
            dl = cmd.split(" ", 2)
            if len(dl) == 3 and dl[0] == "dl":
                self.__download(dl[2])
            if len(dl) == 3 and dl[0] == "up":
                self.__upload(dl[1])
            self.event.wait()
            msg = self.sock.recv(1024 * 1024 * 4)
            print(msg.decode())
            self.sock.send(b"\n")
        self.__stop()

    def __send(self, message):
        self.sock.send(message.encode())

    def __recv(self):
        res = self.sock.recv(1024 * 1024).decode()
        return res

    def __download(self, local_path):
        self.event.clear()
        target_size = int(self.sock.recv(1024).decode())
        bar = ProgressBar(0, target_size)
        bar.run()
        with open(local_path, "wb") as f:
            while True:
                data = self.sock.recv(1024 * 1024 * 4)
                if not data or data == b"finish":
                    self.sock.send(b"finish")
                    break
                f.write(data)
                bar.update(1024 * 1024 * 4)
        while True:
            if bar.finished():
                self.event.set()
                break

    def __upload(self, local_path):
        self.event.clear()
        try:
            with open(local_path, "rb") as f:
                file_data = f.read(1024 * 1024 * 4)  # 每次读取4MB
                while file_data:
                    self.sock.send(file_data)
                    file_data = f.read(1024 * 1024 * 4)
            time.sleep(0.5)
            self.sock.send(b"finish")
            if self.sock.recv(1024) == b"finish":
                print(f"FTP:文件 {local_path} 上传成功")
            else:
                print(f"FTP:文件 {local_path} 上传失败")
        except FileNotFoundError:
            print("FTP:文件{local_path}不存在")
        finally:
            self.event.set()


if __name__ == '__main__':
    print("FTP客户端-个人独立开发")
    print(
        "注：比较简陋，路径请尽量以绝对路径为准（部分地方支持相对路径），测试平台为Linux Mint，注意权限问题、文件名尽量不含空格")
    print("- cd -     在服务器上切换路径，切换上一次的所在路径，而非上一级路径")
    print("- cd home   在服务器上中从根区切换到下一级子目录home目录")
    print("- cd /home  同上")
    print("- ls        当前路径下的所有文件以及文件夹")
    print("- mkdir 文件夹路径\n            创建相对应的文件夹")
    print("- rm 路径    危险指令，删除当前路径对应的的文件或者文件夹（包括非空文件夹）")
    print(
        "- dl 服务器文件名 本地文件路径\n            将所在路径下的服务器文件下载到本地文件，本地文件可被创建，请确保本地文件所处文件夹存在")
    print("- up 本地文件路径 服务器文件名\n            将本地文件上传到所在服务器的路径下，服务器文件可被创建")
    print("- quit      退出客户端")
    print()
    client = FTPClient("127.0.0.1")
    client.run()
