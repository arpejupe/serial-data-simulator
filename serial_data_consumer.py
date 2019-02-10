# -*- coding: utf-8 -*-

from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from serial_data import SerialData
import logging
import pika
import argparse
import time
import json

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

class SerialDataConsumer(object):

    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'topic'
    QUEUE = 'serial_data'
    ROUTING_KEY = 'serial_data'

    def __init__(self, amqp_url, target_topic, batch_messages, iot_client, serial_data):
        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._target_topic = target_topic
        self._batch_messages = int(batch_messages)
        self._iot_client = iot_client
        self._serial_data = serial_data

    def connect(self):
        LOGGER.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     self.on_connection_open,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        LOGGER.info('Connection opened')
        self.add_on_connection_close_callback()
        self.open_channel()

    def add_on_connection_close_callback(self):
        LOGGER.info('Adding connection close callback')
        self._connection.add_on_close_callback(self.on_connection_closed)

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                           reply_code, reply_text)
            self._connection.add_timeout(5, self.reconnect)

    def reconnect(self):
        # This is the old connection IOLoop instance, stop its ioloop
        self._connection.ioloop.stop()

        if not self._closing:

            # Create a new connection
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run
            self._connection.ioloop.start()

    def open_channel(self):
        LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reply_code, reply_text):
        LOGGER.warning('Channel %i was closed: (%s) %s',
                       channel, reply_code, reply_text)
        self._connection.close()

    def setup_exchange(self, exchange_name):
        LOGGER.info('Declaring exchange %s', exchange_name)
        self._channel.exchange_declare(self.on_exchange_declareok,
                                       exchange_name,
                                       self.EXCHANGE_TYPE)

    def on_exchange_declareok(self, unused_frame):
        LOGGER.info('Exchange declared')
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        LOGGER.info('Declaring queue %s', queue_name)
        self._channel.queue_declare(self.on_queue_declareok, queue_name)

    def on_queue_declareok(self, method_frame):
        LOGGER.info('Binding %s to %s with %s',
                    self.EXCHANGE, self.QUEUE, self.ROUTING_KEY)
        self._channel.queue_bind(self.start_consuming, self.QUEUE,
                                 self.EXCHANGE, self.ROUTING_KEY)

    def start_consuming(self, unused_frame):
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self.QUEUE)

    def on_message(self, unused_channel, basic_deliver, properties, body):
        LOGGER.info('Received message # %s from %s: %s',
                    basic_deliver.delivery_tag, properties.app_id, body)
        self.publish_to_iot_client(basic_deliver, body)

    def publish_to_iot_client(self, basic_deliver, body):
        self._serial_data.set_message(body)
        self._serial_data.parse_ascii_to_string().parse_string_to_json()

        if self._batch_messages > 0:
            LOGGER.info('Using batch processing for messages with max message size of %s bytes', self._batch_messages)
            self._serial_data.set_message_max_size(self._batch_messages)
            if not self._serial_data.batch_full:
                self._serial_data.set_batch()
            else:
                LOGGER.info('Publishing a batch message to target topic ... ')
                batch_string = self._serial_data.get_batch()
                self._serial_data.set_message(batch_string)
                self._iot_client.publishAsync(self._target_topic, self._serial_data.message, 1, self.acknowledge_message(basic_deliver.delivery_tag))
                self._serial_data.clear_batch()
        else:
            LOGGER.info('Publishing single messages to target topic ... ')
            self._iot_client.publishAsync(self._target_topic, self._serial_data.message, 1, self.acknowledge_message(basic_deliver.delivery_tag))

    def on_iot_client_message_received(self, client, userdata, message):
        LOGGER.info('IoT Client received a message: %s', message.payload)
        LOGGER.info('Waiting for async publish acknowledgement ...')

    def acknowledge_message(self, delivery_tag):
        LOGGER.info('Acknowledging message %s', delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def stop_consuming(self):
        if self._channel:
            LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self._consumer_tag)

        self._channel.close()

    def run(self):
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        LOGGER.info('Stopping')
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        LOGGER.info('Stopped')

def main():

    parser = argparse.ArgumentParser()

    AllowedActions = ['both', 'publish', 'subscribe']

    parser.add_argument("-l", "--logging", action="store", dest="logging_level", help="Set logging level for MQ", default="info")
    parser.add_argument("-b", "--batch_messages", action="store", dest="batch_messages", help="Set batching of messages instead of sending single lines. Give batch size in bytes", default="0")
    parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
    parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="root_ca.pem")
    parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="aa6562034b-certificate.pem.crt")
    parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="aa6562034b-private.pem.key")
    parser.add_argument("-p", "--port", action="store", dest="port", type=int, help="Port number override")
    parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="serial-data-simulator", help="Targeted client id")
    parser.add_argument("-t", "--topic", action="store", dest="topic", default="rules/DataToDynamo/teknoware/telemetry/RaspberryPI3", help="Targeted topic")
    parser.add_argument("-m", "--mode", action="store", dest="mode", default="both", help="Operation modes: %s"%str(AllowedActions))

    args = parser.parse_args()
    if not args.certificatePath or not args.privateKeyPath:
        parser.error("Missing credentials for authentication.")
        exit(2)

    level = LEVELS.get( args.logging_level, logging.NOTSET)
    logging.basicConfig(level=level)

    logging.debug('Using debug logging ...')
    logging.info('Using info logging ...')

    AWSIotClient = AWSIoTMQTTClient(args.clientId)
    AWSIotClient.configureEndpoint(args.host, args.port)
    AWSIotClient.configureCredentials(args.rootCAPath, args.privateKeyPath, args.certificatePath)
    AWSIotClient.configureAutoReconnectBackoffTime(1, 32, 20)
    AWSIotClient.configureOfflinePublishQueueing(4, 0)  # Infinite offline Publish queueing
    AWSIotClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    AWSIotClient.configureConnectDisconnectTimeout(10)  # 10 sec
    AWSIotClient.configureMQTTOperationTimeout(5)  # 5 sec

    serialData = SerialData()

    serialDataConsumer = SerialDataConsumer(
        amqp_url='amqp://guest:guest@localhost:5672/%2F',
        iot_client=AWSIotClient,
        target_topic=args.topic,
        serial_data=serialData,
        batch_messages=args.batch_messages
    )

    try:
        logging.info('Establishing AWS IoT Connection ...')
        AWSIotClient.connect()
        if args.mode == 'both' or args.mode == 'subscribe':
            AWSIotClient.subscribe(args.topic, 1, serialDataConsumer.on_iot_client_message_received)
        time.sleep(2) # TODO: ensure the connection by using callbacks
        serialDataConsumer.run()

    except KeyboardInterrupt:
        serialDataConsumer.stop()


if __name__ == '__main__':
    main()
