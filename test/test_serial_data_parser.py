import unittest
import sys, json

from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from serial_data import SerialData

class SerialDataParserTest(unittest.TestCase):

    mock_json_object = None
    mock_string = None

    @classmethod
    def setUpClass(cls):
        with open('mock_data.json') as f:
            cls.mock_json_object = json.load(f)
        with open('mock_data.txt') as f:
            cls.mock_string = f.read()

    def test_should_parse_string_to_json_object(self):
        parser = SerialData()
        parser.set_message(self.mock_string)
        parser.parse_string_to_json()
        test_json_object = json.loads(parser.message)
        self.assertEqual(test_json_object, self.mock_json_object)

    def test_should_batch_only_one_line(self):
        parser = SerialData()
        json_line = json.dumps(self.mock_json_object)
        parser.set_message(self.mock_string)
        parser.set_message_max_size(message_max_size=148)
        while not parser.batch_full:
            parser.set_batch()
        self.assertEqual(len(parser.batch), 1)

    def test_should_batch_only_five_lines(self):
        parser = SerialData()
        json_line = json.dumps(self.mock_json_object)
        parser.set_message(self.mock_string)
        parser.set_message_max_size(message_max_size=740)
        while not parser.batch_full:
            parser.set_batch()
        self.assertEqual(len(parser.batch), 5)

if __name__ == '__main__':
    unittest.main()
