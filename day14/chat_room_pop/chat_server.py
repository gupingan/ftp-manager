"""
    即时聊天室服务端，使用面向过程的思想

    author: chujian
    email: ronangu@foxmail.com

    communication protocol: #分隔
    协议头         协议中部            协议尾部
    JOIN        昵称|server            状态
    CHAT            昵称               消息
    QUIT            昵称
"""
from socket import *
from multiprocessing import Process

server_address = ("0.0.0.0", 8888)

user_dict = {}


def protocol(msg):
    head, center, tail = msg.decode().split("#", 2)
    return head, center, tail


def is_duplicated(name):
    for value in user_dict.values():
        if value == name:
            return True
    return False


def listen_join(st, addr, name):
    if "管理员" in name:
        msg = f"JOIN#昵称不允许存在管理员#FALSE"
        st.sendto(msg.encode(), addr)
        return
    if is_duplicated(name):
        msg = f"JOIN#昵称已经被占用#FALSE"
        st.sendto(msg.encode(), addr)
        return
    user_dict[addr] = name
    st.sendto("JOIN#SERVER#TRUE".encode(), addr)
    broadcast(st, addr, f"【公告】{name}", " 进入了聊天室")


def broadcast(st, addr, name, content):
    for key, value in user_dict.items():
        if key == addr:
            continue
        st.sendto(f"{name}{content}".encode(), key)


def handle(st: socket):
    while True:
        client_msg, client_addr = st.recvfrom(1024 * 1024)
        head, center, tail = protocol(client_msg)
        if head == "JOIN":
            listen_join(st, client_addr, center)
        elif head == "CHAT":
            # print(f"\b\b\b\b{center}可以聊天哦~\n>>> ", end="")
            broadcast(st, client_addr, center, f"：{tail}")
        elif head == "QUIT":
            del user_dict[client_addr]
            broadcast(st, client_addr, f"【公告】{center}", " 退出了聊天室")


def main():
    st = socket(AF_INET, SOCK_DGRAM)
    st.bind(server_address)
    recv_process = Process(target=handle, args=(st,), daemon=True)
    recv_process.start()
    while True:
        admin_msg = input(">>> ")
        if not admin_msg:
            continue
        if admin_msg == "close server":
            print("服务器已关闭")
            break
        admin_msg = f"CHAT#【管理员】#{admin_msg}"
        st.sendto(admin_msg.encode(), server_address)
    st.close()


if __name__ == "__main__":
    main()
