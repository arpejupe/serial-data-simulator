import random, json, time, io, csv, logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)

class SerialDataUtils(object):

    def __init__(self):
        pass

    def generate_mock_data(self, min_range=0, max_range=1):
        headings = ['Total runtime','FW ver','Dev ID','Type','inputs','state','Sensor1','Sensor2']
        headings = [cell + '\n' for cell in headings]
        rows = []
        rows.extend(headings)
        for i in range(min_range, max_range):
            totalRuntime = datetime.now()
            FWVer = 'V001'
            devID = 0
            Type = 'Sensor'
            inputs = 8
            state = 'Active'
            Sensor1 = random.randint(0,100)
            Sensor2 = random.randint(0,50)
            values = [str(totalRuntime), str(FWVer), str(devID), Type, str(inputs), state, str(Sensor1), str(Sensor2)]
            values = [cell + '\n' for cell in values]
            #values[-1] = values[-1].replace('\n', '\r\n')
            rows.extend(values)
        LOGGER.debug('Generated random mock data: ', rows)
        return rows
