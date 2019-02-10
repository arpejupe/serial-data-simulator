import time
import argparse
import logging

from serial_data import SerialData
from serial_data_utils import SerialDataUtils

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
                '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}

class SerialPortWriter(object):

    utils = SerialDataUtils()

    def __init__(self, port, interval, serial_data):
        self._serial_port_name = port
        self._serial_port = open(port, "w+")
        self._serial_data = serial_data
        self._interval = float(interval)

    def run(self):
        LOGGER.info('Started writing serial data to port: %s', self._serial_port_name)
        while True:
            mock_data = self.utils.generate_mock_data()
            self._serial_data.set_message(mock_data)
            self._serial_data.parse_csv_to_string().parse_string_to_ascii()
            LOGGER.info('%s', self._serial_data.message)
            self._serial_port.write(self._serial_data.message)
            time.sleep(self._interval)

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("-l", "--logging", action="store", dest="logging_level", help="Set logging level for Serial Data Writer", default="info")
    parser.add_argument("-p", "--port", action="store", dest="serial_port", help="Set serial port to write data", default="/dev/pts/3")
    parser.add_argument("-i", "--interval", action="store", dest="interval", help="Set interval for writing to serial port", default="10")

    args = parser.parse_args()
    level = LEVELS.get(args.logging_level, logging.NOTSET)
    logging.basicConfig(level=level)

    logging.debug('Using debug logging ...')
    logging.info('Using info logging ...')

    serial_data = SerialData()
    serial_port_writer = SerialPortWriter(args.serial_port, args.interval, serial_data)
    serial_port_writer.run()

if __name__ == '__main__':
    main()
