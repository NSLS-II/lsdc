from confluent_kafka import Producer
import os
import sys
import json
from time import sleep

import certifi
import yaml

with open(f"{os.environ['CONFIGDIR']}/nsls2-kafka-config.yml") as f:
    kafka_config = yaml.safe_load(f)

bootstrap_servers = ",".join(kafka_config["bootstrap_servers"])
lsdc_producer_config = kafka_config["lsdc_producer_config"]

conf = {'bootstrap.servers':bootstrap_servers,
        'ssl.ca.location': certifi.where()}
conf.update(lsdc_producer_config)

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


