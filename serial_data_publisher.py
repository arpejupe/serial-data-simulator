# -*- coding: utf-8 -*-

import logging
import pika
import argparse
import json

from serial_port_reader import SerialPortReader

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
                '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

class SerialDataPublisher(object):

    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'topic'
    PUBLISH_INTERVAL = 1
    QUEUE = 'serial_data'
    ROUTING_KEY = 'serial_data'

    def __init__(self, amqp_url, serial_port):
        self._connection = None
        self._channel = None
        self._serial = None

        self._deliveries = None
        self._acked = None
        self._nacked = None
        self._message_number = None

        self._stopping = False
        self._url = amqp_url
        self._serial_port = serial_port

    def connect(self):
        LOGGER.info('Connecting to %s', self._url)
        return pika.SelectConnection(pika.URLParameters(self._url),
                                     on_open_callback=self.on_connection_open,
                                     on_close_callback=self.on_connection_closed,
                                     stop_ioloop_on_close=False)

    def on_connection_open(self, unused_connection):
        LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_closed(self, connection, reply_code, reply_text):
        self._channel = None
        if self._stopping:
            self._connection.ioloop.stop()
        else:
            LOGGER.warning('Connection closed, reopening in 5 seconds: (%s) %s',
                           reply_code, reply_text)
            self._connection.add_timeout(5, self._connection.ioloop.stop)

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
        LOGGER.warning('Channel was closed: (%s) %s', reply_code, reply_text)
        self._channel = None
        if not self._stopping:
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
        self._channel.queue_bind(self.on_bindok, self.QUEUE,
                                 self.EXCHANGE, self.ROUTING_KEY)

    def on_bindok(self, unused_frame):
        LOGGER.info('Queue bound')
        self.start_publishing()

    def start_publishing(self):
        LOGGER.info('Issuing consumer related RPC commands')
        self.enable_delivery_confirmations()
        self.schedule_next_message()

    def enable_delivery_confirmations(self):
        LOGGER.info('Issuing Confirm.Select RPC command')
        self._channel.confirm_delivery(self.on_delivery_confirmation)

    def on_delivery_confirmation(self, method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        LOGGER.info('Received %s for delivery tag: %i',
                    confirmation_type,
                    method_frame.method.delivery_tag)
        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1
        self._deliveries.remove(method_frame.method.delivery_tag)
        LOGGER.info('Published %i messages, %i have yet to be confirmed, '
                    '%i were acked and %i were nacked',
                    self._message_number, len(self._deliveries),
                    self._acked, self._nacked)

    def schedule_next_message(self):
        if self.PUBLISH_INTERVAL > 0:
            LOGGER.info('Scheduling next message for %0.1f seconds',
                        self.PUBLISH_INTERVAL)
            self._connection.add_timeout(self.PUBLISH_INTERVAL,
                                         self.publish_message)
        else:
            LOGGER.info('Scheduling messages without interval')
            self.publish_message()

    def publish_message(self):
        if self._channel is None or not self._channel.is_open:
            return

        properties = pika.BasicProperties(app_id='serial-data-publisher')

        message = False
        while not message:
            message = self._serial_port.read()

        self._channel.basic_publish(self.EXCHANGE, self.ROUTING_KEY,
                                    message,
                                    properties)
        self._message_number += 1
        self._deliveries.append(self._message_number)
        LOGGER.info('Published message # %i', self._message_number)
        self.schedule_next_message()

    def run(self):
        while not self._stopping:
            self._connection = None
            self._deliveries = []
            self._acked = 0
            self._nacked = 0
            self._message_number = 0

            try:
                self._connection = self.connect()
                self._connection.ioloop.start()
            except KeyboardInterrupt:
                self.stop()
                self._serial_port.stop()
                if (self._connection is not None and
                        not self._connection.is_closed):
                    # Finish closing
                    self._connection.ioloop.start()

        LOGGER.info('Stopped')


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--logging", action="store", dest="logging_level", help="Set logging level for Serial Data Reader", default="info")
    parser.add_argument("-p", "--port", action="store", dest="serial_port", help="Set serial port to read data", default="/dev/pts/4")

    args = parser.parse_args()
    level = LEVELS.get(args.logging_level, logging.NOTSET)
    logging.basicConfig(level=level)

    logging.debug('Using debug logging ...')
    logging.info('Using info logging ...')

    serial_port = SerialPortReader()
    serial_port.open(args.serial_port)

    serial_data_publisher = SerialDataPublisher(
        'amqp://guest:guest@localhost:5672/%2F?connection_attempts=3&heartbeat_interval=3600',
        serial_port
    )

    serial_data_publisher.run()


if __name__ == '__main__':
    main()
