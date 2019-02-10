import csv, io, json, logging

LOGGER = logging.getLogger(__name__)

class JsonObject(object):
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
            sort_keys=False, indent=0, separators=(',',':'))

class SerialData(object):

    def __init__(self):
        self.message = ''
        self.batch = []
        self.batch_full = False
        self.message_max_size = 10240 # default 10KB
        self.message_max_size_limit = 131072 # 128KB

    def set_message(self, message):
        self.message = message

    def set_message_max_size(self, message_max_size):
        message_max_size = int(message_max_size)
        if int(message_max_size) < self.message_max_size_limit:
            self.message_max_size = message_max_size
        else:
            self.message_max_size = self.message_max_size_limit

    def set_batch(self):
        if self.get_batch_size() + len(self.message) <= self.message_max_size:
            self.batch.append(self.message)
        else:
            self.batch_full = True
        LOGGER.debug("Batch size: %s", self.get_batch_size())
        return self

    def get_batch(self):
        return self._parse_array_to_string(self.batch)

    def get_batch_size(self):
        return len(self._parse_array_to_string(self.batch))

    def clear_batch(self):
        self.batch = []
        self.batch_full = False

    def parse_ascii_to_string(self):
        input_list = self.message.split(' ')
        self.message = ''.join(unichr(int(ascii)) for ascii in input_list if ascii).replace('\n','')
        return self

    def parse_string_to_json(self):
        json_string = ''
        f = io.StringIO(self.message.decode('utf-8'))
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            json_object = self._build_json_object(row)
            json_string = json_object.toJSON()
        self.message = json_string.replace('\n','')
        return self

    def parse_csv_to_string(self):
        stream_input = io.BytesIO()
        writer = csv.writer(stream_input)
        writer.writerow(self.message)
        self.message = stream_input.getvalue()
        return self

    def parse_string_to_ascii(self):
        asciiChars = [];
        for ch in self.message:
            asciiChars.append(str(ord(ch)))
        asciiString = ' '.join(asciiChars)
        LOGGER.debug('ASCII printing: %s', asciiString)
        self.message = asciiString
        return self

    def _parse_array_to_string(self, array):
        json_array = ''
        json_array += "[" + ",".join(element for element in array) + "]"
        return json_array

    def _build_json_object(self, params):
        obj = JsonObject()
        attributes = params[:8]
        values = params[8:]
        for i in range(len(attributes)):
            setattr(obj, attributes[i], values[i])
        return obj
