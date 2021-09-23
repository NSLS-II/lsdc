from confluent_kafka import Producer
import os
import sys
import json
from time import sleep

import certifi

conf = {'bootstrap.servers':os.environ["KAFKA_SERVERS"],
        'security.protocol': 'SSL',
        'ssl.ca.location': certifi.where()}
p = Producer(**conf)

def delivery_callback(err, msg):
    if err:
        sys.stderr.write('%% Message failed delivery: %s\n' % err)
        sys.exit(1)
    else:
        sys.stderr.write('%% Message delivered to %s [%d] @ %d\n' %
                        (msg.topic(), msg.partition(), msg.offset()))

def send_kafka_message(topic, event, uuid, protocol, **kwargs):
    try:
        if protocol in ("standard", "vector") or (protocol == "raster" and event == "stop"):
            message = {"event":event, "uuid":uuid, "protocol":protocol}
        elif protocol == "raster" and event == "event":
            message = {"event":event, "uuid":uuid, "protocol":protocol, "row":kwargs["row"], "proc_flag":kwargs["proc_flag"]}
        else:
            raise Exception(f'Unhandled protocol/event combination: protocol={protocol} event={event}')
        p.produce(topic, json.dumps(message), callback=delivery_callback)
    except BufferError:
        sys.stderr.write('%% Local producer queue is full(%d messages awaiting delivery): try again\n' %
            len(p))


