import socket
import threading
import tkinter as tk
from tkinter import ttk, simpledialog

# -----------------------------
# Config
# -----------------------------
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5050

EMOJIS = [
    "☼˖°(•‿•)°˖☼",
    "☼˖°(•ᴗ•)°˖☼",
    "☼˖°(•︵•)°˖☼",
    "☼˖°(•̀ᴗ•́)°˖☼",
    "☼˖°(•o•)°˖☼"
]

AVATARS = [
    "Solín ☼",
    "Pingüi nuevo 🐧",
    "Robotín 🤖",
    "Flamenca 🕊️",
    "Andasol 🌞"
]

THEMES = {
    "Guadalinex Green": {
        "bg": "#e8f5e9",
        "chat_bg": "#ffffff",
        "chat_fg": "#1b5e20",
        "accent": "#66bb6a",
        "accent_soft": "#a5d6a7"
    },
    "Retro CRT": {
        "bg": "#001b00",
        "chat_bg": "#000000",
        "chat_fg": "#00ff66",
        "accent": "#00aa44",
        "accent_soft": "#004422"
    },
    "Andalusian Blue": {
        "bg": "#e3f2fd",
        "chat_bg": "#ffffff",
        "chat_fg": "#0d47a1",
        "accent": "#42a5f5",
        "accent_soft": "#bbdefb"
    }
}


class GuadalChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Guadalchat")
        self.root.geometry("600x650")

        self.current_theme_name = "Guadalinex Green"
        self.theme = THEMES[self.current_theme_name]

        self.username = None
        self.avatar = None

        self.sock = None
        self.connected = False

        self.crt_phase = 0

        self.build_ui()
        self.apply_theme()
        self.ask_identity_and_connect()
        self.start_crt_animation()

    # -----------------------------
    # UI
    # -----------------------------
    def build_ui(self):
        self.root.configure(bg=self.theme["bg"])

        # Top bar: theme + status
        top_frame = tk.Frame(self.root, bg=self.theme["bg"])
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(
            top_frame,
            text="Tema:",
            bg=self.theme["bg"],
            fg=self.theme["chat_fg"],
            font=("Consolas", 10, "bold")
        ).pack(side="left")

        self.theme_var = tk.StringVar(value=self.current_theme_name)
        theme_menu = ttk.Combobox(
            top_frame,
            textvariable=self.theme_var,
            values=list(THEMES.keys()),
            state="readonly",
            width=20
        )
        theme_menu.pack(side="left", padx=5)
        theme_menu.bind("<<ComboboxSelected>>", self.on_theme_change)

        self.status_label = tk.Label(
            top_frame,
            text="Desconectado",
            bg=self.theme["bg"],
            fg=self.theme["chat_fg"],
            font=("Consolas", 10)
        )
        self.status_label.pack(side="right")

        # Tape / activity bar
        self.tape_label = tk.Label(
            self.root,
            text="▌▌▌",
            bg=self.theme["bg"],
            fg=self.theme["accent"],
            font=("Consolas", 10)
        )
        self.tape_label.pack(fill="x")

        # Chat area
        self.chat_frame = tk.Frame(self.root, bg=self.theme["bg"])
        self.chat_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.chat_box = tk.Text(
            self.chat_frame,
            wrap="word",
            state="disabled",
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"],
            font=("Consolas", 12)
        )
        self.chat_box.pack(fill="both", expand=True)

        # Entry area
        self.entry_frame = tk.Frame(self.root, bg=self.theme["bg"])
        self.entry_frame.pack(fill="x", padx=10, pady=5)

        self.entry = tk.Entry(
            self.entry_frame,
            font=("Consolas", 12),
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"]
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry.bind("<Return>", self.send_message)

        send_btn = tk.Button(
            self.entry_frame,
            text="Enviar",
            command=self.send_message,
            font=("Consolas", 12, "bold")
        )
        send_btn.pack(side="right")
        self.send_btn = send_btn

        # Bottom buttons
        bottom_frame = tk.Frame(self.root, bg=self.theme["bg"])
        bottom_frame.pack(fill="x", padx=10, pady=5)

        emoji_btn = tk.Button(
            bottom_frame,
            text="Emojis ☼",
            command=self.open_emoji_picker,
            font=("Consolas", 11)
        )
        emoji_btn.pack(side="left")

        avatar_btn = tk.Button(
            bottom_frame,
            text="Avatar",
            command=self.change_avatar,
            font=("Consolas", 11)
        )
        avatar_btn.pack(side="left", padx=5)

        reconnect_btn = tk.Button(
            bottom_frame,
            text="Reconectar",
            command=self.reconnect,
            font=("Consolas", 11)
        )
        reconnect_btn.pack(side="right")

        test_btn = tk.Button(
            bottom_frame,
            text="Test llamada",
            command=self.start_test_call,
            font=("Consolas", 11)
        )
        test_btn.pack(side="right", padx=5)

        self.buttons = {
            "emoji": emoji_btn,
            "avatar": avatar_btn,
            "reconnect": reconnect_btn,
            "test": test_btn
        }

    def apply_theme(self):
        self.theme = THEMES[self.theme_var.get()]
        self.root.configure(bg=self.theme["bg"])

        self.chat_frame.configure(bg=self.theme["bg"])
        self.entry_frame.configure(bg=self.theme["bg"])
        self.tape_label.configure(bg=self.theme["bg"], fg=self.theme["accent"])

        self.chat_box.configure(
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"]
        )
        self.entry.configure(
            bg=self.theme["chat_bg"],
            fg=self.theme["chat_fg"]
        )

        self.status_label.configure(
            bg=self.theme["bg"],
            fg=self.theme["chat_fg"]
        )

        self.send_btn.configure(
            bg=self.theme["accent"],
            fg="white",
            activebackground=self.theme["accent_soft"]
        )

        for b in self.buttons.values():
            b.configure(
                bg=self.theme["accent_soft"],
                fg=self.theme["chat_fg"],
                activebackground=self.theme["accent"]
            )

    def on_theme_change(self, event=None):
        self.apply_theme()
        self.add_system_message(f"Tema cambiado a: {self.theme_var.get()}")

    # -----------------------------
    # Identity & connection
    # -----------------------------
    def ask_identity_and_connect(self):
        self.username = simpledialog.askstring("Nombre", "Introduce tu nombre de usuario:")
        if not self.username:
            self.username = "Invitado"

        self.avatar = AVATARS[0]

        host = simpledialog.askstring("Servidor", f"IP del servidor ({DEFAULT_HOST}):")
        if not host:
            host = DEFAULT_HOST

        port_str = simpledialog.askstring("Puerto", f"Puerto ({DEFAULT_PORT}):")
        if not port_str:
            port = DEFAULT_PORT
        else:
            try:
                port = int(port_str)
            except ValueError:
                port = DEFAULT_PORT

        self.connect(host, port)

    def connect(self, host, port):
        if self.connected:
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.connected = True
            self.status_label.config(text=f"Conectado a {host}:{port}")
            self.add_system_message("Conectado al servidor.")
            threading.Thread(target=self.receive_loop, daemon=True).start()
            self.send_system_join()
        except Exception as e:
            self.connected = False
            self.status_label.config(text="Error de conexión")
            self.add_system_message(f"Error al conectar: {e}")

    def reconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.connected = False
        self.status_label.config(text="Reconectando...")
        self.ask_identity_and_connect()

    # -----------------------------
    # Networking
    # -----------------------------
    def receive_loop(self):
        try:
            while self.connected:
                data = self.sock.recv(4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="ignore")
                self.add_message_raw(text)
        except:
            pass
        finally:
            self.connected = False
            self.status_label.config(text="Desconectado")
            self.add_system_message("Desconectado del servidor.")

    def send_raw(self, text):
        if not self.connected or not self.sock:
            self.add_system_message("No conectado.")
            return
        try:
            self.sock.sendall(text.encode("utf-8"))
        except Exception as e:
            self.add_system_message(f"Error al enviar: {e}")
            self.connected = False

    def send_system_join(self):
        msg = f"[JOIN] {self.avatar} {self.username} se ha unido a Guadalchat."
        self.send_raw(msg)

    # -----------------------------
    # Messaging
    # -----------------------------
    def send_message(self, event=None):
        msg = self.entry.get().strip()
        if not msg:
            return
        full = f"{self.avatar} {self.username}: {msg}"
        self.add_message_raw(full)
        self.send_raw(full)
        self.entry.delete(0, tk.END)

    def add_message_raw(self, text):
        self.chat_box.config(state="normal")
        self.chat_box.insert("end", text + "\n")
        self.chat_box.config(state="disabled")
        self.chat_box.see("end")

    def add_system_message(self, text):
        self.chat_box.config(state="normal")
        self.chat_box.insert("end", f"[Sistema] {text}\n")
        self.chat_box.config(state="disabled")
        self.chat_box.see("end")

    # -----------------------------
    # Emoji picker
    # -----------------------------
    def open_emoji_picker(self):
        picker = tk.Toplevel(self.root)
        picker.title("Emojis de Solín")
        picker.geometry("260x220")
        picker.configure(bg=self.theme["bg"])

        for emoji in EMOJIS:
            btn = tk.Button(
                picker,
                text=emoji,
                font=("Consolas", 12),
                bg=self.theme["accent_soft"],
                fg=self.theme["chat_fg"],
                activebackground=self.theme["accent"],
                command=lambda e=emoji, w=picker: self.insert_emoji_and_close(e, w)
            )
            btn.pack(fill="x", pady=3, padx=10)

    def insert_emoji_and_close(self, emoji, window):
        self.entry.insert("end", emoji)
        window.destroy()

    # -----------------------------
    # Avatar selection
    # -----------------------------
    def change_avatar(self):
        picker = tk.Toplevel(self.root)
        picker.title("Seleccionar avatar")
        picker.geometry("260x220")
        picker.configure(bg=self.theme["bg"])

        tk.Label(
            picker,
            text="Elige tu avatar:",
            bg=self.theme["bg"],
            fg=self.theme["chat_fg"],
            font=("Consolas", 11, "bold")
        ).pack(pady=5)

        for av in AVATARS:
            btn = tk.Button(
                picker,
                text=av,
                font=("Consolas", 11),
                bg=self.theme["accent_soft"],
                fg=self.theme["chat_fg"],
                activebackground=self.theme["accent"],
                command=lambda a=av, w=picker: self.set_avatar(a, w)
            )
            btn.pack(fill="x", pady=3, padx=10)

    def set_avatar(self, avatar, window):
        self.avatar = avatar
        self.add_system_message(f"Avatar cambiado a: {avatar}")
        window.destroy()

    # -----------------------------
    # Test call (service contact)
    # -----------------------------
    def start_test_call(self):
        if not self.connected:
            self.add_system_message("No conectado. No se puede iniciar la prueba.")
            return
        cmd = f"[TESTCALL] {self.avatar} {self.username}"
        self.add_system_message("Iniciando prueba con contacto de servicio GuadalTest...")
        self.send_raw(cmd)

    # -----------------------------
    # Retro animation (CRT + tape)
    # -----------------------------
    def start_crt_animation(self):
        self.crt_phase = (self.crt_phase + 1) % 4
        patterns = ["▌▌▌", "▌ ▌", " ▌ ", "▌ ▌"]
        self.tape_label.config(text=patterns[self.crt_phase])

        if self.theme_var.get() == "Retro CRT":
            if self.crt_phase % 2 == 0:
                self.chat_box.configure(bg="#000000")
            else:
                self.chat_box.configure(bg="#001000")

        self.root.after(200, self.start_crt_animation)


if __name__ == "__main__":
    root = tk.Tk()
    app = GuadalChatClient(root)
    root.mainloop()
