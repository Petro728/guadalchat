import socket
import threading
import time
import os
import sys
import re

HOST = "127.0.0.1"
PORT = 5050

clients = {}          # conn -> username
client_ips = {}       # conn -> ip
banned_ips = set()    # banned IPs
muted_users = set()   # normalized usernames

BANNED_IPS_FILE = "banned_ips.txt"

start_time = time.time()
lock = threading.Lock()


def load_banned_ips():
    if not os.path.exists(BANNED_IPS_FILE):
        return
    with open(BANNED_IPS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            ip = line.strip()
            if ip:
                banned_ips.add(ip)


def save_banned_ips():
    with open(BANNED_IPS_FILE, "w", encoding="utf-8") as f:
        for ip in sorted(banned_ips):
            f.write(ip + "\n")


def clean_name(name: str) -> str:
    name = re.sub(r"[\u200B-\u200F\uFEFF]", "", name)
    name = " ".join(name.strip().split())
    return name.lower()


def broadcast(msg, exclude=None):
    with lock:
        for conn in list(clients.keys()):
            if conn is exclude:
                continue
            try:
                conn.sendall(msg.encode("utf-8"))
            except:
                pass


def send_to(conn, msg):
    try:
        conn.sendall(msg.encode("utf-8"))
    except:
        pass


def kick_conn(conn):
    name = clients.get(conn)
    if not name:
        return False

    send_to(conn, "[SERVER] Has sido expulsado por el administrador.")
    try:
        conn.sendall(b"\n")
        time.sleep(0.2)
    except:
        pass

    ip = client_ips.get(conn)

    conn.close()
    if conn in clients:
        del clients[conn]
    if conn in client_ips:
        del client_ips[conn]

    if name:
        broadcast(f"[SERVER] {name} ha sido expulsado.")
    print(f"[SERVER] Expulsado: {name} ({ip})")
    return True


def kickid(user_id):
    with lock:
        if user_id < 1 or user_id > len(clients):
            return False
        conn = list(clients.keys())[user_id - 1]
        return kick_conn(conn)


def banid(user_id):
    with lock:
        if user_id < 1 or user_id > len(clients):
            return None

        conn = list(clients.keys())[user_id - 1]
        ip = client_ips.get(conn)
        if not ip:
            return None

        banned_ips.add(ip)
        save_banned_ips()
        kick_conn(conn)
        return ip


def banip(ip: str):
    with lock:
        banned_ips.add(ip)
        save_banned_ips()
        # Kick any current connections from that IP
        for conn, cip in list(client_ips.items()):
            if cip == ip:
                kick_conn(conn)


def unbanip(ip: str):
    with lock:
        if ip in banned_ips:
            banned_ips.remove(ip)
            save_banned_ips()
            return True
        return False


def server_stats():
    uptime = int(time.time() - start_time)
    return (
        f"[SERVER] Estadísticas:\n"
        f" - Usuarios conectados: {len(clients)}\n"
        f" - Uptime: {uptime} segundos\n"
        f" - IPs baneadas: {len(banned_ips)}\n"
    )


def handle_client(conn, addr):
    ip = addr[0]

    # IP ban check BEFORE anything else
    with lock:
        if ip in banned_ips:
            try:
                send_to(conn, "[SERVER] Tu IP está baneada.")
                conn.sendall(b"\n")
                time.sleep(0.25)
            except:
                pass
            conn.close()
            print(f"[SERVER] Conexión rechazada (IP baneada): {ip}")
            return

    print(f"[+] Conectado: {addr}")
    username = None
    username_clean = None

    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            text = data.decode("utf-8", errors="ignore")

            if text.startswith("[JOIN]"):
                username = text.replace("[JOIN]", "").strip()
                username_clean = clean_name(username)

                with lock:
                    clients[conn] = username
                    client_ips[conn] = ip

                broadcast(f"[SERVER] {username} se ha unido al chat.")
                continue

            if text.startswith("[TESTCALL]"):
                send_to(conn, "[GuadalTest] OK\n")
                continue

            with lock:
                if username_clean in muted_users:
                    send_to(conn, "[SERVER] Estás muteado.")
                    continue

            broadcast(text, exclude=conn)

    except:
        pass

    finally:
        with lock:
            if conn in clients:
                name = clients[conn]
                del clients[conn]
                if conn in client_ips:
                    del client_ips[conn]
                broadcast(f"[SERVER] {name} ha salido del chat.")
        conn.close()
        print(f"[-] Desconectado: {addr}")


def console_commands():
    while True:
        cmd = input().strip()

        if cmd == "/list":
            print("[SERVER] Usuarios conectados:")
            with lock:
                for i, (conn, name) in enumerate(clients.items(), start=1):
                    ip = client_ips.get(conn, "?")
                    print(f" {i}: {repr(name)} @ {ip}")

        elif cmd.startswith("/whois "):
            try:
                uid = int(cmd.split()[1])
                with lock:
                    if uid < 1 or uid > len(clients):
                        print("[SERVER] ID inválido.")
                    else:
                        conn = list(clients.keys())[uid - 1]
                        name = clients.get(conn, "?")
                        ip = client_ips.get(conn, "?")
                        print(f"[SERVER] WHOIS {uid}: {name} @ {ip}")
            except:
                print("[SERVER] Uso: /whois <id>")

        elif cmd.startswith("/kickid "):
            try:
                uid = int(cmd.split()[1])
                if kickid(uid):
                    print("[SERVER] Usuario expulsado.")
                else:
                    print("[SERVER] ID inválido.")
            except:
                print("[SERVER] Uso: /kickid <id>")

        elif cmd.startswith("/banid "):
            try:
                uid = int(cmd.split()[1])
                ip = banid(uid)
                if ip:
                    print(f"[SERVER] IP baneada: {ip}")
                else:
                    print("[SERVER] ID inválido.")
            except:
                print("[SERVER] Uso: /banid <id>")

        elif cmd.startswith("/banip "):
            ip = cmd.split(" ", 1)[1].strip()
            banip(ip)
            print(f"[SERVER] IP baneada manualmente: {ip}")

        elif cmd.startswith("/unbanip "):
            ip = cmd.split(" ", 1)[1].strip()
            if unbanip(ip):
                print(f"[SERVER] IP desbaneada: {ip}")
            else:
                print("[SERVER] Esa IP no estaba baneada.")

        elif cmd.startswith("/broadcast "):
            msg = cmd.split(" ", 1)[1]
            broadcast(f"[SERVER BROADCAST] {msg}")
            print("[SERVER] Mensaje enviado.")

        elif cmd == "/stats":
            print(server_stats())

        elif cmd == "/restart":
            print("[SERVER] Reiniciando...")
            os.execv(sys.executable, ["python"] + sys.argv)

        elif cmd == "/shutdown":
            print("[SERVER] Apagando...")
            os._exit(0)

        else:
            print("[SERVER] Comandos:")
            print(" /list")
            print(" /whois <id>")
            print(" /kickid <id>")
            print(" /banid <id>")
            print(" /banip <ip>")
            print(" /unbanip <ip>")
            print(" /broadcast <msg>")
            print(" /stats")
            print(" /restart")
            print(" /shutdown")


def main():
    load_banned_ips()
    threading.Thread(target=console_commands, daemon=True).start()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[SERVER] Escuchando en {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
