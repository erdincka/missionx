import json
import os
import random
from time import sleep
from uuid import uuid4
import importlib_resources
from nicegui import app
from files import putfile
from helpers import *
from streams import consume, produce
from tables import find_document_by_id, upsert_document

logger = logging.getLogger()
 
# HQ SERVICES

@fire_and_forget
def nasa_feed_service():
    """
    Simulate recieving events from NASA API, send random notification messages every NASA_FEED_INTERVAL seconds to TOPIC_NASAFEED, 
    and save notification message into TABLE
    """

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_LOCAL}"
    table_path = f"{HQ_VOLUME_PATH}/{HQ_IMAGETABLE}"

    # get the items
    input_data = None
    with open(
        importlib_resources.files("main").joinpath(
            NASA_FEED_FILE
        ),
        "r",
    ) as f:
        input_data = json.load(f)

    # enabled at start
    app.storage.general["services"]["nasafeed"] = True

    items = input_data["collection"]["items"]
    logger.info("Loaded %d messages for NASA Feed", len(items))
 
    output_topic_name = f"{stream_path}:{TOPIC_NASAFEED}"

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("nasafeed", False):
            logger.debug("sleeping...")
            sleep(NASA_FEED_DELAY)
            continue

        logger.debug("running...")
        count = random.randrange(5)

        # pick "count" random items
        for item in random.sample(items, count):
            # assign a unique ID for table
            item["_id"] = str(uuid4())

            if upsert_document(host=os.environ['MAPR_IP'], table=table_path, json_dict=item):

                logger.info(
                    "Event notification from NASA: %s",
                    item["data"][0]["title"]
                )

            else:
                logger.warning("Saving event notification failed for %s", item['data'][0]['title'])

            # push message to pipeline stream
            message = {
                "description": "New image event received from NASA.",
                "tablename": table_path.split("/").pop(),
                "assetID": item["_id"],
                "messageCreatorID": "ezshow",
            }

            if produce(stream_path, TOPIC_NASAFEED, [json.dumps(message)]):

                logger.info("Published image received event to %s", output_topic_name)
                # notify ui that we have new message
                app.storage.general["nasafeed_count"] = app.storage.general.get("nasafeed_count", 0) + 1
            else:
                logger.warning("Publish failed for assetID %s", message['assetID'])

            # add random delay between events (0 to 1 sec)
            sleep(random.random())

        # add delay to publishing
        sleep(NASA_FEED_DELAY)

@fire_and_forget
def image_download_service():
    """
    Subscribe to TOPIC_NASAFEED and download/save assets (images) for published events into IMAGE_FILE_LOCATION
    Update TABLE with new download location and publish an event to notify downloaded/failed image to TOPIC_IMAGE_DOWNLOADED
    """

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_LOCAL}"
    table_path = f"{HQ_VOLUME_PATH}/{HQ_IMAGETABLE}"

    input_topic = TOPIC_NASAFEED
    output_topic = TOPIC_IMAGE_DOWNLOADED

    app.storage.general["services"]["imagedownload"] = True
    logger.info("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("imagedownload", False):
            logger.debug("Image download service is turned off, sleeping...")
            sleep(IMAGE_DOWNLOAD_SERVICE_DELAY)
            continue

        logger.debug("running...")
        downloaded = 0
        failed = 0

        for msg in consume(stream=stream_path, topic=input_topic):
            record = json.loads(msg)
            logger.debug("Received: %s", record)

            doc = find_document_by_id(host=os.environ["MAPR_IP"], table=table_path, docid=record["assetID"])
            logger.debug("Found: %s", str(doc))

            if doc is None:
                logger.warning("Asset not found %s", imageFilename)
                failed += 1

            else:
                # lazily get the last part of href - should be the filename
                assetUrl = doc["links"][0]["href"]
                imageFilename = assetUrl.split("/").pop()

                logger.info("Downloading asset for %s", doc['data'][0]['title'])

                newMessage = {
                    "description": "New image file downloaded from NASA.",
                    "assetID": doc['_id']
                }

                # put file to downloadLocation
                response = putfile(
                    host=os.environ["MAPR_IP"],
                    file=f"images/{imageFilename}", 
                    destfolder=IMAGE_FILE_LOCATION
                )

                if response is not None:
                    logger.debug(
                        "Asset saved in folder %s/%s", HQ_VOLUME_PATH, IMAGE_FILE_LOCATION
                    )

                    # update DB with new location
                    doc["imageDownloadLocation"] = f"{HQ_VOLUME_PATH}/{IMAGE_FILE_LOCATION}/{imageFilename}"

                    if upsert_document(host=os.environ["MAPR_IP"], table=table_path, json_dict=doc):
                        logger.debug("Document updated with new location")
                        newMessage['status'] = "success"
                        downloaded += 1

                    else:
                        logger.warning("Failed to update document %s for asset location", doc['_id'])
                        newMessage['status'] = "failed"
                        failed += 1

                    # Publish image saved message to output stream
                    if produce(stream=stream_path, topic=output_topic, messages=[json.dumps(newMessage)]):
                        logger.debug("Published image download event to %s", f"{stream_path}:{output_topic}")
                        # notify ui that we have new message
                        app.storage.general["imagedownload_count"] = app.storage.general.get("imagedownload_count", 0) + 1
                        app.storage.general["hqimages"].append(tuple([doc['data'][0]['title'], doc["imageDownloadLocation"]]))
                    else:
                        logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", newMessage)

        logger.debug("Image download service -> OK: %d, FAIL: %d", downloaded, failed)

        # add delay to publishing
        sleep(IMAGE_DOWNLOAD_SERVICE_DELAY)


@fire_and_forget
def asset_broadcast_service():
    """
    Subscribe to IMAGE_DOWNLOAD topic and publist to ASSET_BROADCAST to notify edge clusters for new asset availability
    """

    logger = logging.getLogger("devel")
    logger.setLevel(logging.DEBUG)

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_LOCAL}"

    input_topic = TOPIC_IMAGE_DOWNLOADED
    output_topic = TOPIC_ASSET_BROADCAST

    app.storage.general["services"]["assetbroadcast"] = True
    logger.info("started...")

    while True:
        # skip if service is disabled by user
        if not app.storage.general["services"].get("assetbroadcast", False):
            logger.debug("Asset Broadcast service is turned off, sleeping...")
            sleep(ASSET_BROADCAST_DELAY)
            continue

        logger.debug("running...")

        for msg in consume(stream=stream_path, topic=input_topic):
            record = json.loads(msg)
            logger.debug("Received: %s", record)

            # Publish to output topic
            if produce(stream=stream_path, topic=output_topic, messages=[msg]):
                logger.info("Published asset to %s", f"{stream_path}:{output_topic}")
                # notify ui that we have new message
                app.storage.general["assetbroadcast_count"] = app.storage.general.get("assetbroadcast_count", 0) + 1
            else:
                logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", record)

        # add delay to publishing
        sleep(ASSET_BROADCAST_DELAY)
