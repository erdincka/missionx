import logging
from time import sleep
import timeit

from helpers import BROADCAST_LISTENER_DELAY


logger = logging.getLogger()

def produce(stream: str, topic: str, messages: list):
    from confluent_kafka import Producer

    p = Producer({"streams.producer.default.stream": stream})

    try:
        for message in messages:
            p.produce(topic, message.encode("utf-8"))

    except Exception as error:
        logger.warning(error)
        return False
    
    finally:
        p.flush()

    return True

def consume(stream: str, topic: str):
    from confluent_kafka import Consumer, KafkaError

    consumer = Consumer(
        {"group.id": "ezshow", "default.topic.config": {"auto.offset.reset": "earliest"}}
    )

    consumer.subscribe([f"{stream}:{topic}"])

    running = True
    start_time = timeit.default_timer()

    while running:
        try:
            message = consumer.poll(timeout=1.0)

            if message is None: continue

            if not message.error():
                yield message.value().decode("utf-8")

            elif message.error().code() == KafkaError._PARTITION_EOF:
                running = False
                continue

            # silently ignore other errors
            else:
                logger.debug(message.error())

            # terminate after 2 sec
            # TODO: re-consider when to timeout
            if timeit.default_timer() - 2 >= start_time:
                running = False

            # delay poll
            sleep(0.2)

        except Exception as error:
            logger.debug(error)
            running = False

    consumer.close()
