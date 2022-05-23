from os import environ
import pygame as p

environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

########################################################################################################################
# Default Interface Constants

nickname_message = 'Please choose a nickname'
app_title = 'Science Chat App'
topic_window_size = '400x150'
options = ["Mathematics", "Computer Science", "Physics"]
server_error_msg = 'Error! (server may be down!'
combo_box_binding = '<<ComboboxSelected>>'
topic_label_msg = 'Please Choose at least 2 topics!'
topic_button_msg = 'Start Chatting'
tkinter_exit = 'WM_DELETE_WINDOW'
client_exit_msg = 'Client Stopped!'
localhost = '127.0.0.1'
port = 9090
p.init()
colours = ['light blue', 'light yellow', 'light purple']
cloud_amqp_connection = 'amqps://twkybiil:j9nwdZ3W17b9wNOpxPbaF1o15QBAS4vZ@kangaroo.rmq.cloudamqp.com/twkybiil'
url = 'CLOUDAMQP_URL'
chat_queue = 'chat_queue'
token_timer = 10


def stop_before_connection():
    print(client_exit_msg)
    exit(0)
