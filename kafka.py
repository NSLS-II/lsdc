from confluent_kafka import Producer
import sys
import json
from time import sleep

topic = f'{beamline}.lsdc.collection'

conf = {'bootstrap.servers':servers}
p = Producer(**conf)

def delivery_callback(err, msg):
    if err:
        sys.stderr.write('%% Message failed delivery: %s\n' % err)
        sys.exit(1)
    else:
        sys.stderr.write('%% Message delivered to %s [%d] @ %d\n' %
                        (msg.topic(), msg.partition(), msg.offset()))

def send_kafka_message(uuid, protocol, topic=topic):
    if not uuid or not protocol:
        raise Exception("No uuid or protocol specified")
    try:
        message = {'uuid':uuid, 'protocol':protocol)
        p.produce(topic, json.dumps(message), callback=delivery_callback)
    except BufferError:
        sys.stderr.write('%% Local producer queue is full(%d messages awaiting delivery): try again\n' %
            len(p))


