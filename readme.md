Serial Data Simulator
============

## Purpose
Set of scripts to simulate typical IoT data flow i.e from a sensor mcu to a
gateway device through serial ports, and then finally over the internet to the
cloud.

How it works:
- Application starts to send mock data to a pseudo serial port.
- Then it reads the port and sends the data to a message queue.
- Message queue is being subscribed by a single consumer that pulls messages from
queue and sends them into cloud via AWS Client.
- Before sending the messages consumer parses the data and converts it into JSON
- AWS Device gateway receives messages and they get ingested with rules
to DynamoDB.
- To optimize the traffic over the internet, messages can be sent in single units
or in a batch.
- Message queue persists the data in case of AWS Client is offline. Messages that
are not acknowledged by the server will be ultimately sent back to queue, and
consumer will try sending them again to the AWS Gateway when client is back online.
- Application can be run on automatically on device boot or restart


## Structural View

  * *serial_port_writer*: Module that opens serial port and starts to write mock
  data to a pseudo serial port. Serial data to be written is an ASCII format
  CSV containing line feeds and carriage returns to mark the end of the data
  line in a data stream.
  * *serial_port_reader:* Module that reads data from pseudo serial port. Injected
  as dependency to SerialDataPublisher
  * *serial_data_publisher:* Message queue publisher to push messages to the
  serial data queue. Uses SerialPortReader as dependency to read serial data
  from pseudoport.
  * *serial_data_consumer:* Message queue consumer to pull messages from serial
  data queue made by using RabbitMQ. Uses AWSMQTTClient as dependency to send
  data to AWS IoT Device Gateway asynchronously on success callbacks. Before
  sending the data to cloud ASCII form data is parsed into JSON string.
  * *serial_data:* Model for serial data with set of parser functions
  * *serial_data_utils:* Set of utility functions for processing serial data
  * *supervisord:* Process control system for starting and restarting script on
  boot or exception

## Dependencies

  * RabbitMQ (Pika)
  * aws-iot-python-sdk
  * socat
  * supervisor

## Installation

1) Install all dependencies for running the scripts:
```
pip install AWSIoTPythonSDK pika supervisor
```

2) Before running scripts create pseudo ports in following way:
```
sudo apt-get update && sudo apt-get install socat
socat -d -d pty,raw,echo=0 pty,raw,echo=0
```

You will see which ports were created, one is used for writing and the other
reading.

3) Setup your AWS DynamoDB table to store serial data. You can use DeviceId as
primary key and timestamp as sort key

4) Create a rule that saves IoT data to dynamoDB with Rules Engine.
Define query statement and SQL Add insert dynamoDB action to your rule.

5) Register Thing in AWS and create certificates and IoT Policy, attach those
policies to a device certificate and attach certificate to thing. More info:
https://docs.aws.amazon.com/iot/latest/developerguide/iot-gs.html

6) Download and place certificates in certificates folder. They should look
something like this:
```
./certificates/aa6562034b-certificate.pem.crt
./certificates/aa6562034b-private.pem.key
./certificates/root_ca.pem
```

7) Finally the scripts can be run, preferably in order as follows
```
python serial_port_writer.py -p "/dev/pts/3"
python serial_data_publisher.py -p "/dev/pts/4"
python serial_data_consumer.py -e akd1r4fx9bo59-ats.iot.eu-west-1.amazonaws.com -r certificates/root_ca.pem -c certificates/aa6562034b-certificate.pem.crt -k certificates/aa6562034b-private.pem.key -p 8883
```

8) You can use *supervisor* (or any other way such as systemd to run the scripts on
system boot)

Create supervisord.conf file and place following line end of the file:
```
[program:serial-data-writer]
command=python -u ../serial-data-simulator/serial_data_writer.py
autostart=true
autorestart=true
stderr_logfile=/var/log/writer.err.log
stdout_logfile=/var/log/writer.out.log
redirect_stderr=true
```

For more detailed installation instructions please see:
http://supervisord.org/running.html

## Run parameters

You can set following run parameters for each script:

Writer
- p for serial port
- l for logging level
- i for serial write interval. For example 10 would write one serial line in 10
seconds interval

For Publisher:
- p for serial port
- l for logging level

For Consumer:
- b for using batch processing. Give batch size in bytes i.e 1024
- l for debugging level
- p for RabbitMQ Port number override
- t for AWS topic to send serial data to. Use rules/ path to use basic ingest


## Author
Copyright © 2019, Arttu Pekkarinen
