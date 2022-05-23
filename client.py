import socket
import threading
from tkinter import *
import tkinter.scrolledtext
from tkinter import simpledialog
from tkinter import ttk
from PythonChatroomGUI import constants as k
import time
import pika
import os

########################################################################################################################
# Client Side

HOST = k.localhost
PORT = k.port


class Client:
    def __init__(self, host, port):
        self.message = tkinter.Tk()
        self.message.withdraw()
        self.host = host
        self.port = port
        self.socket = None
        self.chat_root = None
        self.topic_counter = 0
        self.colour_counter = 0
        self.topic_label = None
        self.time_label = None
        self.seconds = None
        self.token_holder = None
        self.token_label = None
        self.unsent_messages = []
        self.url = os.environ.get(k.url,
                                  k.cloud_amqp_connection)

        self.params = pika.URLParameters(self.url)
        self.connection = pika.BlockingConnection(self.params)
        self.channel = self.connection.channel()

        self.nickname = simpledialog.askstring(k.app_title, k.nickname_message, parent=self.message)
        self.channel.queue_declare(queue=f'{k.chat_queue}:{self.nickname}')

        if self.nickname is None or self.nickname == '':
            k.stop_before_connection()

        self.topics = []
        self.topic_root = tkinter.Tk()
        self.topic_root.configure(bg='lavender')
        self.topic_root.title(string=k.app_title)
        self.topic_root.geometry(k.topic_window_size)
        self.options = k.options
        self.clicked = StringVar()
        self.clicked.set(self.options[0])
        self.topic_combo_box = ttk.Combobox(self.topic_root, value=self.options)
        self.running = True
        self.gui_done = False
        self.text_area = None
        self.input_area = None
        self.topic_gui()

########################################################################################################################
# Topic selection logic (can't select a topic twice)

    def topic_clicker(self, event):
        if self.topic_combo_box.get() not in self.topics:
            tkinter.Label(self.topic_root, text=self.topic_combo_box.get()).pack()
            self.topics.append(self.topic_combo_box.get())

########################################################################################################################
# Server connection (after 2 or more topics are chosen)

    def init_chat(self):
        if len(self.topics) >= 2:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
                gui_thread = threading.Thread(target=self.gui_loop)
                receive_thread = threading.Thread(target=self.receive)
                self.topic_root.destroy()
                gui_thread.start()
                receive_thread.start()
            except:
                print(k.server_error_msg)
                self.socket.close()

########################################################################################################################
# Topic seleciton GUI

    def topic_gui(self):
        self.topic_combo_box.bind(k.combo_box_binding, self.topic_clicker)
        self.topic_combo_box.pack()
        tkinter.Label(self.topic_root, text=k.topic_label_msg).pack(padx=20, pady=5)
        start_button = tkinter.Button(self.topic_root, text=k.topic_button_msg, command=self.init_chat)
        start_button.config(font=('Arial', 12))
        start_button.pack(padx=20, pady=5)
        self.topic_root.mainloop()

########################################################################################################################
# Timer label updating

    def update_time(self):
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        second = time.strftime('%S')
        am_pm = time.strftime('%p')
        time_zone = time.strftime('%Z')
        self.time_label.config(text=hour + ":" + minute + ":" + second + " " + am_pm + " " + time_zone)
        self.time_label.after(1000, self.update_time)

########################################################################################################################
# Chat window GUI

    def gui_loop(self):
        self.chat_root = tkinter.Tk()
        self.chat_root.title(string=k.app_title)
        self.chat_root.configure(bg='lavender')
        chat_label = tkinter.Label(self.chat_root, text=f'Chat (as {self.nickname}):', bg='lightgray')
        chat_label.config(font=('Arial', 12))
        chat_label.pack(padx=20, pady=5)

        self.text_area = tkinter.scrolledtext.ScrolledText(self.chat_root)
        self.text_area.pack(padx=20, pady=5)
        self.text_area.config(state='disabled')

        message_label = tkinter.Label(self.chat_root, text='Message:', bg='lightgray')
        message_label.config(font=('Arial', 12))
        message_label.pack(padx=20, pady=5)

        self.topic_label = tkinter.Label(self.chat_root,
                                         text=f'Current topic: {self.topics[self.topic_counter % len(self.topics)]}',
                                         bg=k.colours[self.colour_counter])
        self.topic_label.config(font=('Arial', 12))
        self.topic_label.pack(padx=20)

        self.time_label = Label(self.chat_root, text="Clock Time:")
        self.time_label.config(font=('Arial', 12))
        self.time_label.pack(padx=20, pady=5)
        self.update_time()

        self.token_label = tkinter.Label(self.chat_root, text='Token:', bg='lightgray')
        self.token_label.config(font=('Arial', 12))
        self.token_label.pack(padx=20, pady=5)

        self.input_area = tkinter.Text(self.chat_root, height=3)
        self.input_area.pack(padx=20, pady=5)

        send_button = tkinter.Button(self.chat_root, text='Send', command=self.write)
        send_button.config(font=('Arial', 12))
        send_button.pack(padx=20, pady=5)
        self.gui_done = True
        self.chat_root.protocol(k.tkinter_exit, self.stop_connection)
        self.chat_root.mainloop()

########################################################################################################################
# Send button logic - only the token holder can send the message - multicast to all clients with same topic

    def write(self):
        message = f"{self.topics[self.topic_counter % len(self.topics)]}: [{self.nickname}]: " \
                  f"{self.input_area.get('1.0', 'end')}"

        if len(self.unsent_messages) != 0:
            message = message + f' + Unsent Messages: {self.unsent_messages}' + '\n'

        if self.nickname == self.token_holder:
            self.topic_counter += 1
            self.colour_counter += 1
            self.socket.send(message.encode('utf-8'))
            self.topic_label.config(text=self.topics[self.topic_counter % len(self.topics)])
            self.input_area.delete('1.0', 'end')
            self.unsent_messages = []
        else:
            self.channel.basic_publish(exchange='',
                                       routing_key=f'{k.chat_queue}:{self.nickname}',
                                       body=message.encode('utf-8'))
            self.unsent_messages.append(self.input_area.get('1.0', 'end').strip('\n'))

########################################################################################################################
# Connection failure handler

    def stop_connection(self):
        self.socket.close()
        print(k.client_exit_msg)
        exit(0)

########################################################################################################################
# Client listener (waits for server messages)
# Messages:
#   Token -> the client can send messages
#   Nickname -> the client chooses his/her nickname
#   Topic -> the client sends the chosen topics to the server
#   Other -> normal chat message (multicast)

    def receive(self):
        while self.running:
            try:
                message = self.socket.recv(1024).decode('utf-8')
                if '(Token)' in str(message):
                    self.token_holder = message.split(':', 1)[1]
                    self.token_label.config(text=self.token_holder)
                elif message == 'Nickname':
                    self.socket.send(self.nickname.encode('utf-8'))
                elif message == 'Topic':
                    topics_to_send = str(self.topics)
                    topics_to_send = topics_to_send.encode('utf-8')
                    self.socket.send(topics_to_send)
                else:
                    if self.gui_done:
                        self.text_area.config(state='normal')
                        self.text_area.insert('end', message)
                        self.text_area.yview('end')
                        self.text_area.config(state='disabled')
            except ConnectionAbortedError:
                break
            except:
                print("Error!")
                self.socket.close()
                break


client = Client(HOST, PORT)
