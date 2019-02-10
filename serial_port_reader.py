import serial
import logging

LOGGER = logging.getLogger(__name__)

class SerialPortReader(object):

    def __init__(self):
        self.serial_port = None
        self.serial_port_name = ''
        self.output = ''
        self.CRLF = False

    def open(self, port="/dev/pts/4"):
        self.serial_port = serial.Serial(port, 9600, rtscts=True,dsrdtr=True)
        self.serial_port_name = port
        LOGGER.info('Started reading output from port: %s', self.serial_port_name)

    def stop(self):
        self.serial_port.close()

    def read(self):
        self.output += self.serial_port.read(1)
        output_list = self.output.split(' ')

        for index, value in enumerate(output_list):
            if index >= 1 and value == '10' and output_list[index-1] == '13':
                if self.CRLF:
                    message = ' '.join(element for element in output_list if element)
                    LOGGER.debug('Read complete line: %s', message)
                    self.CRLF = True
                    del output_list[:]
                    self.output = ''
                    return message
                self.CRLF = True
                del output_list[:]
                self.output = ''
