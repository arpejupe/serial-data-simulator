from serial_port_reader import SerialPortReade

import pika
import socket
import time

serial_port = SerialPortReader()
serial_port.open("/dev/pts/4")

mqconnection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
mqchannel = mqconnection.channel()
mqchannel.queue_declare(queue='serial_data')

while True:
    message = False
    while not message:
        message = self._serial_port.read()
    mqchannel.basic_publish(exchange='',
                          routing_key='serial_data',
                          body=message)
    time.sleep(1)
