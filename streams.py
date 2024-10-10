import logging
from time import sleep
import timeit

from common import MAX_POLL_TIME


logger = logging.getLogger("streams")

def produce(cluster: str, stream: str, topic: str, record: str):
    from confluent_kafka import Producer

    p = Producer({"streams.producer.default.stream": stream})

    try:
        logger.debug("pushing message: %s", record)
        p.produce(topic, record.encode("utf-8"))

    except Exception as error:
        logger.warning(error)
        return False

    finally:
        p.flush()

    return True


def consume(cluster: str, stream: str, topic: str):
    from confluent_kafka import Consumer, KafkaError

    consumer = Consumer(
        {"group.id": "ezshow", "default.topic.config": {"auto.offset.reset": "earliest"}}
    )

    consumer.subscribe([f"{stream}:{topic}"])

    # logger.debug("polling %s", topic)
    start_time = timeit.default_timer()

    try:
        while True:
            # enforce timeout so we don't run forever
            if timeit.default_timer() - MAX_POLL_TIME > start_time:
                raise TimeoutError

            message = consumer.poll(timeout=MAX_POLL_TIME)

            if message is None: continue

            if not message.error(): yield message.value().decode("utf-8")

            elif message.error().code() == KafkaError._PARTITION_EOF:
                raise EOFError
            # silently ignore other errors
            else: logger.debug(message.error())

            # add delay
            sleep(0.1)

    except Exception as error:
        logger.debug(error)

    finally:
        consumer.close()
