import socket
import threading
import constants as k
import time
import pika
import os
from os import environ

########################################################################################################################
# Server side

environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

HOST = k.localhost
PORT = k.port

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))

server.listen()

clients = []
nicknames = []
nicknames_topics = {}
token_log = []


def print_topic_list():
    print("Clients and topics chosen: ", end='')
    for nickname in nicknames_topics:
        print(nickname, '->', nicknames_topics[nickname])


def print_client_list():
    print("Client list: ", end='')
    for client in clients:
        print(f'{nicknames[clients.index(client)]} ', end='')
    print("")


########################################################################################################################
# Send message to all connected clients

def broadcast(message):
    for client in clients:
        client.send(message)


########################################################################################################################
# Send message to all clients with the respective topic

def multicast_topic(message, topic):
    for client in clients:
        if topic in nicknames_topics[nicknames[clients.index(client)]]:
            client.send(message)

########################################################################################################################
# Process client messages (multicast, exit, etc.)


def handle(client):
    while True:
        try:
            message = client.recv(1024)
            print(f'{nicknames[clients.index(client)]} has sent a message.')
            topic = message.decode('utf-8')
            topic = topic.split(':', 1)[0]
            multicast_topic(message, topic)
        except:
            print(f'{nicknames[clients.index(client)]} has lost the connection.')
            nicknames_topics.pop(nicknames[clients.index(client)])
            nicknames.remove(nicknames[clients.index(client)])
            clients.remove(client)
            client.close()
            break


########################################################################################################################
# Pass token to the next client available (10 seconds timer)

def token_logic(seconds=0, token=0):
    while True:
        client_number = len(clients)
        if client_number != 0:
            seconds += 1
            if seconds % k.token_timer == 0:
                token += 1
                broadcast(f'(Token):{nicknames[token % client_number]}'.encode('utf-8'))
        else:
            seconds = 0
            token = 0
        time.sleep(1)

########################################################################################################################
# Cloud AMQP Consumer (new queue for every client)


def consume_messages():
    url = os.environ.get(k.url,
                         k.cloud_amqp_connection)
    params = pika.URLParameters(url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    for client in clients:
        channel.queue_declare(queue=f'{k.chat_queue}:{nicknames[clients.index(client)]}')

    def callback(ch, method, properties, body):
        print("Added to the queue message: " + str(body.decode('utf-8')), end="")

    for client in clients:
        channel.basic_consume(f'{k.chat_queue}:{nicknames[clients.index(client)]}',
                              callback,
                              auto_ack=True)
        channel.start_consuming()

########################################################################################################################
# Server listener (waits for client messages, accepts new connections)


def receive():
    while True:
        client, address = server.accept()
        hour = time.strftime('%H')
        minute = time.strftime('%M')
        second = time.strftime('%S')
        am_pm = time.strftime('%p')

        print(f'Connected with {str(address)} at {hour}:{minute}:{second} {am_pm}')
        client.send('Nickname'.encode('utf-8'))

        nickname = client.recv(1024)
        nickname = nickname.strip().decode('utf-8')
        nicknames.append(nickname)
        clients.append(client)

        client.send('Topic'.encode('utf-8'))
        received_topics = client.recv(1024)
        received_topics = received_topics.decode('utf-8')
        received_topics = eval(received_topics)

        nicknames_topics[nickname] = received_topics

        print_topic_list()
        broadcast(f'{nickname} has joined the chat.\n'.encode('utf-8'))
        client.send('Connected to the server'.encode('utf-8'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

########################################################################################################################
# Thread setup (connection listener, token timer and Cloud AMQP consumer)

print("Server running...")
timer_thread = threading.Thread(target=token_logic)
receive_thread = threading.Thread(target=receive)
consumer_thread = threading.Thread(target=consume_messages)
timer_thread.start()
receive_thread.start()
consumer_thread.start()
