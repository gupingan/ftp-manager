"""
    即时聊天室客户端，使用面向过程的思想

    author: chujian
    email: ronangu@foxmail.com

    communication protocol: #分隔
    协议头         协议中部            协议尾部
    JOIN        昵称|server            状态
    CHAT            昵称               消息
    QUIT            昵称
"""
import time
from socket import *
from multiprocessing import Process

server_address = ("0.0.0.0", 8888)


def protocol(msg):
    head, center, tail = msg.decode().split("#", 2)
    return head, center, tail


def join(st):
    while True:
        name = input("请输入聊天昵称(至少3位)：")
        if " " in name or "#" in name or len(name) < 3:
            print("系统提示：昵称不合法")
            continue
        content = f"JOIN#{name}#"
        st.sendto(content.encode(), server_address)
        time.sleep(0.1)
        msg, addr = st.recvfrom(1024)
        head, center, tail = protocol(msg)
        if head == "JOIN" and tail == "FALSE":
            print(f"登录失败：{center}")
            continue
        if head == "JOIN" and tail == "TRUE":
            print("【公告】你加入了聊天室")
            return name


def chat(st, name):
    while True:
        message = input(">>> ")
        if message == "quit":
            client_msg = f"QUIT#{name}#"
            st.sendto(client_msg.encode(), server_address)
            print("【公告】你退出了聊天室")
            break
        client_msg = f"CHAT#{name}#{message}"
        st.sendto(client_msg.encode(), server_address)


def recv(st):
    while True:
        msg, addr = st.recvfrom(1024 * 1024)
        print(f"\b\b\b\b{msg.decode()}\n>>> ", end="")


def main():
    st = socket(AF_INET, SOCK_DGRAM)
    name = join(st)
    recv_process = Process(target=recv, args=(st,), daemon=True)
    recv_process.start()
    chat(st, name)
    st.close()


if __name__ == "__main__":
    main()
