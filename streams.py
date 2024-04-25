import logging


logger = logging.getLogger("streams")

def produce(stream: str, topic: str, messages: list):
    from confluent_kafka import Producer

    p = Producer({"streams.producer.default.stream": stream})

    try:
        for message in messages:
            p.produce(topic, message.encode("utf-8"))

    except Exception as error:
        logger.debug(error)
    
    finally:
        p.flush()


def consume(stream: str, topic: str):
    from confluent_kafka import Consumer, KafkaError

    c = Consumer(
        {"group.id": "mygroup", "default.topic.config": {"auto.offset.reset": "earliest"}}
    )
    c.subscribe([f"{stream}:{topic}"])
    running = True
    while running:
        msg = c.poll(timeout=1.0)
        if msg is None:
            continue
        if not msg.error():
            print("Received message: %s" % msg.value().decode("utf-8"))
        elif msg.error().code() != KafkaError._PARTITION_EOF:
            print(msg.error())
            running = False
    c.close()
