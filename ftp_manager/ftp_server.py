import shutil
import sys
import time
from threading import Thread
from socket import *

import os


class File:
    """
        linux下可以使用os.access(path, os.R_OK)检查权限问题
        未做权限检查处理，win平台需要安装第三方库pywin32，使用win32security检查权限
    """
    def __init__(self):
        self.current_path = os.path.abspath(os.sep)
        self.parent_path = os.path.abspath(os.path.join(self.current_path, os.pardir))
        if not os.path.isdir(self.parent_path):
            self.parent_path = None
        self.separator = os.sep

    def ls(self):
        items = os.scandir(self.current_path)  # 使用os.scandir()函数代替os.listdir()函数，这样可以减少系统调用次数，提高性能
        files = []
        directories = []
        for item in items:
            path = os.path.join(self.current_path, item)
            if os.path.isfile(path):
                files.append(item.name)
            elif os.path.isdir(path):
                directories.append(item.name)
        return {"files": sorted(files), "directories": sorted(directories)}

    @staticmethod
    def format(ls_msg: dict):
        res = ""
        count = 0
        for key, value in ls_msg.items():
            if key == "files":
                index = 1
                value_len = len(value)
                count += value_len
                res += f"文件({value_len})：\n"
                for v in value:
                    res += f"{index}. {v}   "
                    if index % 3 == 0:
                        res += "\n"
                    index += 1
                res += "\n"
            else:
                index = 1
                value_len = len(value)
                count += value_len
                res += f"文件夹({value_len})：\n"
                for v in value:
                    res += f"{index}. {v}   "
                    if index % 3 == 0:
                        res += "\n"
                    index += 1
        res += f"\nFTP:当前路径下，所包含的文件和文件夹共计 {count}"
        return res

    def cd(self, directory):
        if directory == "-":
            if self.parent_path is not None:
                self.current_path = self.parent_path
                self.parent_path = os.path.abspath(os.path.join(self.current_path, os.pardir))
                if not os.path.isdir(self.parent_path):
                    self.parent_path = None
        else:
            path = os.path.abspath(os.path.join(self.current_path, directory))
            if os.path.isdir(path):
                self.parent_path = self.current_path
                self.current_path = path

    def pwd(self):
        return self.current_path

    def mkdir(self, directory):
        if os.path.isabs(directory):
            os.makedirs(directory, exist_ok=True)
        else:
            path = os.path.abspath(os.path.join(self.current_path, directory))
            os.makedirs(path, exist_ok=True)

    def rm(self, directory):
        if os.path.isabs(directory):
            if os.path.isfile(directory):
                os.remove(directory)
            elif os.path.isdir(directory):
                shutil.rmtree(directory)
        else:
            path = os.path.abspath(os.path.join(self.current_path, directory))
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)


class Handle(Thread):
    def __init__(self, conn: socket, addr: tuple):
        self.conn, self.addr = conn, addr
        self.file = File()
        self.current_path = self.file.pwd()
        super().__init__()

    def run(self):
        while True:
            self.current_path = self.file.pwd()
            self.conn.send(self.current_path.encode())
            cmd = self.conn.recv(1024 * 1024)
            cmd = cmd.decode().split(" ", 1)
            if cmd[0] in ("quit", "exit"):
                print(f"客户端 {self.addr} 断开连接")
                break
            elif cmd[0] == "ls":
                res_dict = self.file.ls()
                res = self.file.format(res_dict)
            elif cmd[0] == "pwd":
                res = self.current_path
            elif cmd[0] == "cd" and len(cmd) == 2:
                self.file.cd(cmd[1])
                res = f"FTP:您已选择路径 {self.file.pwd()}"
            elif cmd[0] == "mkdir" and len(cmd) == 2:
                try:
                    self.file.mkdir(cmd[1])
                    res = f"FTP:您已创建文件夹 {cmd[1]}"
                except Exception:
                    res = "FTP:创建失败"
            elif cmd[0] == "rm" and len(cmd) == 2:
                try:
                    self.file.rm(cmd[1])
                    res = f"FTP:您已删除 {cmd[1]}"
                except Exception:
                    res = "FTP:删除失败"
            elif cmd[0] == "dl":
                try:
                    cmd = " ".join(cmd).split(" ", 2)
                    if len(cmd) != 3:
                        continue
                    size = os.path.getsize(os.path.join(self.current_path, cmd[1]))
                    self.conn.send(str(size).encode())
                    time.sleep(0.5)
                    with open(os.path.join(self.current_path, cmd[1]), "rb") as f:
                        file_data = f.read(1024 * 1024 * 4)  # 每次读取4MB
                        while file_data:
                            self.conn.send(file_data)
                            file_data = f.read(1024 * 1024 * 4)
                    time.sleep(0.5)
                    self.conn.send(b"finish")
                    if self.conn.recv(1024) == b"finish":
                        res = f"FTP:文件 {cmd[1]} 下载成功"
                    else:
                        res = f"FTP:文件 {cmd[1]} 下载失败"
                except FileNotFoundError:
                    res = f"FTP:文件{cmd[1]}不存在"
            elif cmd[0] == "up":
                cmd = " ".join(cmd).split(" ", 2)
                if len(cmd) != 3:
                    continue
                with open(os.path.join(self.current_path, cmd[2]), "wb") as f:
                    while True:
                        data = self.conn.recv(1024 * 1024 * 4)
                        print(data)
                        if not data or data == b"finish":
                            self.conn.send(b"finish")
                            break
                        f.write(data)
                    res = "FTP:已接收文件"
            else:
                res = " "

            self.conn.send(str(res).encode())
            self.conn.recv(1024)
        self.conn.close()


class FTPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8888, listen_count: int = 5):
        self.host, self.port = host, port
        self.listen_count = listen_count
        self.server_addr = (self.host, self.port)
        self.sock = socket(AF_INET, SOCK_STREAM)

    def __create(self):
        self.sock.bind(self.server_addr)
        print("服务端 绑定地址中......")
        self.sock.listen(self.listen_count)
        print(f"服务端 创建中，监听等待队列容量：{self.listen_count}")

    def run(self, run_handle: Handle = None):
        run_handle = run_handle or Handle
        self.__create()
        while True:
            print(f"服务端 {self.server_addr} 等待连接中......")
            try:
                conn, addr = self.sock.accept()
                print(f"客户端 {addr} 建立连接")
            except KeyboardInterrupt:
                self.sock.close()
                sys.exit("服务端 优雅的退出了~")
            handle = run_handle(conn, addr)
            handle.start()


if __name__ == '__main__':
    server = FTPServer()
    server.run()
