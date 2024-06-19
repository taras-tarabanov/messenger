import socket
import threading
import json
import struct
from PIL import Image, ImageTk, ImageDraw
import io
from tkinter import Tk, Text, Entry, Button, END, Label, Scrollbar, Toplevel, StringVar, Canvas, Frame, LEFT, RIGHT, BOTH, colorchooser

class ChatClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Chat Client")

        self.image_refs = []  # List to keep references to images

        # Username input dialog
        self.login_window = Toplevel(self.master)
        self.login_window.title("Login")
        Label(self.login_window, text="Enter username:").pack(side="top", fill="x")
        self.username_entry = Entry(self.login_window)
        self.username_entry.pack(side="top", fill="x")
        Button(self.login_window, text="Login", command=self.login).pack(side="top")

        # Username display label
        self.username_label = Label(self.master, text="", font=("Arial", 14))
        self.username_label.pack(pady=10)

        # Main chat window
        self.chat_frame = Text(self.master, state='disabled', width=50, height=20, wrap='word')
        self.chat_frame.pack(padx=20, pady=5)

        scrollbar = Scrollbar(self.master, command=self.chat_frame.yview)
        scrollbar.pack(side='right', fill='y')
        self.chat_frame['yscrollcommand'] = scrollbar.set

        # Partial messages label
        self.partial_message_var = StringVar(self.master)
        self.partial_message_label = Label(self.master, textvariable=self.partial_message_var, fg='grey')
        self.partial_message_label.pack(fill="x", padx=20, pady=1)

        # Message entry
        self.message_entry = Entry(self.master)
        self.message_entry.pack(fill="x", padx=20, pady=5)
        self.message_entry.bind("<KeyRelease>", self.notify_server_of_partial_message)
        self.message_entry.bind("<Return>", self.send_message)

        # Frame for buttons and drawing
        self.button_drawing_frame = Frame(self.master)
        self.button_drawing_frame.pack(fill="x", padx=20, pady=5)

        # Send text button
        Button(self.button_drawing_frame, text="Send Text", command=self.send_message).pack(side=LEFT, padx=5)

        # Send image button
        Button(self.button_drawing_frame, text="Send Image", command=self.send_sticker).pack(side=LEFT, padx=5)

        # Drawing canvas
        self.canvas = Canvas(self.button_drawing_frame, width=100, height=100, bg="white")
        self.canvas.pack(side=LEFT, padx=5)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.drawing_color = "black"

        # Create a Pillow image to draw on
        self.canvas_image = Image.new("RGB", (100, 100), "white")
        self.draw = ImageDraw.Draw(self.canvas_image)

        # Color buttons
        colors = ["black", "red", "green", "blue", "yellow"]
        self.color_buttons = Frame(self.button_drawing_frame)
        self.color_buttons.pack(side=LEFT, padx=5)
        for color in colors:
            Button(self.color_buttons, bg=color, width=2, command=lambda col=color: self.set_color(col)).pack(side=LEFT)

        # Send drawing button
        Button(self.button_drawing_frame, text="→", command=self.send_drawing).pack(side=LEFT, padx=5)

        self.master.protocol("WM_DELETE_WINDOW", self.logout)

        # Networking setup
        self.host = '127.0.0.1'
        self.port = 65432
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))

        # Start the thread to listen to messages from the server
        threading.Thread(target=self.receive_message, daemon=True).start()

    def login(self):
        username = self.username_entry.get()
        if username:
            self.username = username
            self.username_label.config(text=f"Logged in as: {username}")
            self.login_window.destroy()
            self.send({'type': 'login', 'username': username})

    def send(self, data):
        try:
            data = json.dumps(data).encode('utf-8')
            self.client_socket.send(struct.pack('>I', len(data)) + data)
        except Exception as e:
            self.chat_frame.config(state='normal')
            self.chat_frame.insert(END, f"Failed to send message: {e}\n")
            self.chat_frame.config(state='disabled')

    def notify_server_of_partial_message(self, event=None):
        message = self.message_entry.get()
        if message:
            self.send({'type': 'partial_message', 'message': message})

    def send_message(self, event=None):
        message = self.message_entry.get()
        self.message_entry.delete(0, END)
        if message:
            self.send({'type': 'message', 'message': message})
            self.display_own_message(message)

    def send_sticker(self):
        sticker_path = r"C:\Users\overheaven\Downloads\photo_2024-05-21_12-23-58.jpg"
        with open(sticker_path, "rb") as f:
            sticker_data = f.read()
        self.send({'type': 'sticker'})
        self.client_socket.send(struct.pack('>I', len(sticker_data)) + sticker_data)
        self.display_own_sticker(sticker_path)

    def send_drawing(self):
        drawing_data = self.get_canvas_image_data()
        self.send({'type': 'drawing'})
        self.client_socket.send(struct.pack('>I', len(drawing_data)) + drawing_data)
        self.display_own_drawing(drawing_data)

    def receive_message(self):
        while True:
            try:
                msg_len = struct.unpack('>I', self.client_socket.recv(4))[0]
                message = self.client_socket.recv(msg_len).decode('utf-8')
                data = json.loads(message)
                self.display_message(data)
                if data["type"] == "sticker":
                    sticker_len = struct.unpack('>I', self.client_socket.recv(4))[0]
                    sticker_data = self.client_socket.recv(sticker_len)
                    self.display_sticker(data["sender"], sticker_data)
                elif data["type"] == "drawing":
                    drawing_len = struct.unpack('>I', self.client_socket.recv(4))[0]
                    drawing_data = self.client_socket.recv(drawing_len)
                    self.display_drawing(data["sender"], drawing_data)
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def display_message(self, data):
        message_type = data.get("type")
        if message_type == "message":
            sender = data.get("sender")
            message = data.get("message")
            self.chat_frame.config(state='normal')
            self.chat_frame.insert(END, f"{sender}: {message}\n")
            self.chat_frame.config(state='disabled')
            self.chat_frame.yview(END)
        elif message_type == "whisper":
            sender = data.get("sender")
            message = data.get("message")
            self.chat_frame.config(state='normal')
            self.chat_frame.insert(END, f"{sender} (whisper): {message}\n", ('whisper',))
            self.chat_frame.tag_configure('whisper', foreground='purple')
            self.chat_frame.config(state='disabled')
            self.chat_frame.yview(END)
        elif message_type == "partial_message":
            sender = data.get("sender")
            message = data.get("message")
            if sender != self.username:
                self.partial_message_var.set(f"{sender} is typing: {message}")
        elif message_type == "online_status":
            online_users = data.get("online_users")
            self.chat_frame.config(state='normal')
            self.chat_frame.insert(END, f"Online users: {', '.join(online_users)}\n")
            self.chat_frame.config(state='disabled')
            self.chat_frame.yview(END)

    def display_sticker(self, sender, sticker_data):
        sticker_image = Image.open(io.BytesIO(sticker_data))
        sticker_image = sticker_image.resize((140, 140), Image.ANTIALIAS)
        sticker_photo = ImageTk.PhotoImage(sticker_image)
        self.image_refs.append(sticker_photo)  # Keep a reference to the image

        self.chat_frame.config(state='normal')
        self.chat_frame.insert(END, "\n")
        self.chat_frame.window_create(END, window=Label(self.chat_frame, text=f"{sender}: ", anchor="w"))
        self.chat_frame.image_create(END, image=sticker_photo)
        self.chat_frame.insert(END, "\n")
        self.chat_frame.config(state='disabled')
        self.chat_frame.yview(END)

    def display_drawing(self, sender, drawing_data):
        drawing_image = Image.open(io.BytesIO(drawing_data))
        drawing_image = drawing_image.resize((100, 100), Image.ANTIALIAS)
        drawing_photo = ImageTk.PhotoImage(drawing_image)
        self.image_refs.append(drawing_photo)  # Keep a reference to the image

        self.chat_frame.config(state='normal')
        self.chat_frame.insert(END, "\n")
        self.chat_frame.window_create(END, window=Label(self.chat_frame, text=f"{sender}: ", anchor="w"))
        self.chat_frame.image_create(END, image=drawing_photo)
        self.chat_frame.insert(END, "\n")
        self.chat_frame.config(state='disabled')
        self.chat_frame.yview(END)

    def display_own_message(self, message):
        self.chat_frame.config(state='normal')
        self.chat_frame.insert(END, f"You: {message}\n")
        self.chat_frame.config(state='disabled')
        self.chat_frame.see(END)

    def display_own_sticker(self, sticker_path):
        sticker_image = Image.open(sticker_path)
        sticker_image = sticker_image.resize((140, 140), Image.ANTIALIAS)
        sticker_photo = ImageTk.PhotoImage(sticker_image)
        self.image_refs.append(sticker_photo)  # Keep a reference to the image

        self.chat_frame.config(state='normal')
        self.chat_frame.insert(END, "\n")
        self.chat_frame.window_create(END, window=Label(self.chat_frame, text="You: ", anchor="w"))
        self.chat_frame.image_create(END, image=sticker_photo)
        self.chat_frame.insert(END, "\n")
        self.chat_frame.config(state='disabled')
        self.chat_frame.yview(END)

    def display_own_drawing(self, drawing_data):
        drawing_image = Image.open(io.BytesIO(drawing_data))
        drawing_image = drawing_image.resize((100, 100), Image.ANTIALIAS)
        drawing_photo = ImageTk.PhotoImage(drawing_image)
        self.image_refs.append(drawing_photo)  # Keep a reference to the image

        self.chat_frame.config(state='normal')
        self.chat_frame.insert(END, "\n")
        self.chat_frame.window_create(END, window=Label(self.chat_frame, text="You: ", anchor="w"))
        self.chat_frame.image_create(END, image=drawing_photo)
        self.chat_frame.insert(END, "\n")
        self.chat_frame.config(state='disabled')
        self.chat_frame.yview(END)

    def get_canvas_image_data(self):
        image_data = io.BytesIO()
        self.canvas_image.save(image_data, format='PNG')
        image_data.seek(0)
        return image_data.read()

    def paint(self, event):
        x1, y1 = (event.x - 1), (event.y - 1)
        x2, y2 = (event.x + 1), (event.y + 1)
        self.canvas.create_oval(x1, y1, x2, y2, fill=self.drawing_color, outline=self.drawing_color)
        self.draw.ellipse([x1, y1, x2, y2], fill=self.drawing_color, outline=self.drawing_color)

    def set_color(self, new_color):
        self.drawing_color = new_color

    def logout(self):
        self.send({'type': 'logout'})
        self.client_socket.close()
        self.master.destroy()

if __name__ == "__main__":
    root = Tk()
    client = ChatClient(root)
    root.mainloop()
