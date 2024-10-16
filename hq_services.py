import json
from posixpath import basename
import random
import shutil
from time import sleep
from uuid import uuid4
import importlib_resources
from sites import *
from files import putfile

from helpers import *
from common import *
from streams import consume, produce
from tables import find_document_by_id, upsert_document

logger = logging.getLogger(__name__)

services = HQSite['services']
tiles = HQSite['tiles']
assets = HQSite['assets']

# HQ SERVICES

def image_feed_service(host: str, user: str, password: str):
    """
    Simulate recieving events from IMAGE API, send random notification messages every IMAGE_FEED_INTERVAL seconds to TOPIC_IMAGEFEED,
    and save notification message into TABLE
    """

    service = services["imagefeed"]

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_PIPELINE}"
    table_path = HQ_IMAGETABLE

    # load mock feed data from file
    input_data = None
    with open(
        importlib_resources.files("main").joinpath(
            IMAGE_FEED_FILE
        ),
        "r",
    ) as f:
        input_data = json.load(f)

    # logger.debug("IMAGE feed data: %s", input_data)

    # notify user
    service["active"] = True

    items = input_data["collection"]["items"]
    logger.debug("Loaded %d messages for IMAGE Feed", len(items))

    output_topic_path = f"{stream_path}:{TOPIC_IMAGEFEED}"

    # skip if service is disabled by user -- shouldn't come here - possibly safe to remove
    if not service["active"]:
        logger.debug("is disabled")
        return

    count = random.randrange(5) + 1

    # pick "count" random items
    for item in random.sample(items, count):
        # assign a unique ID for table
        item["_id"] = str(uuid4().hex[:12])

        if upsert_document(host=host, user=user, password=password, table=table_path, json_dict=item):

            logger.info(
                "Event notification from IMAGE: %s",
                item["data"][0]["title"]
            )

        else:
            logger.warning("Saving event notification failed for %s", item['data'][0]['title'])

        # push message to pipeline stream
        message = {
            "title": item["data"][0]["title"],
            "description": item["data"][0]["description"],
            "tablename": table_path.split("/").pop(),
            "assetID": item["_id"],
            "messageCreatorID": "ezshow",
        }
        if produce(stream=stream_path, topic=TOPIC_IMAGEFEED, record=json.dumps(message)):
            logger.info("Published image received event to %s", output_topic_path)
            # notify ui that we have new message
            # app.storage.general["imagefeed_count"] = app.storage.general.get("imagefeed_count", 0) + 1
            service["count"] += 1
            # update dashboard tiles with new message
            tiles.append(
                tuple(["IMAGE Feed Service", f"Asset: {message['assetID']}", "New asset available from IMAGE", None])
            )

        else:
            logger.warning("Publish failed for assetID %s", message['assetID'])

        # add random delay between events (0 to 1 sec)
        sleep(random.random())

    # add delay to publishing
    # sleep(app.storage.general.get('imagefeed_delay', 1.0))


def image_download_service(host: str, user: str, password: str):
    """
    Subscribe to TOPIC_IMAGEFEED and download/save assets (images) for published events into IMAGE_FILE_LOCATION
    Update TABLE with new download location and publish an event to notify downloaded/failed image to TOPIC_IMAGE_DOWNLOADED
    """

    service = services["imagedownload"]

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_PIPELINE}"
    table_path = HQ_IMAGETABLE

    input_topic = TOPIC_IMAGEFEED
    output_topic = TOPIC_IMAGE_DOWNLOAD

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        logger.debug("is disabled")
        return

    downloaded = 0
    failed = 0

    for msg in consume(stream=stream_path, topic=input_topic):
        try:
            record: dict = json.loads(msg)
            logger.debug("Received: %s", record['title'])

            doc = find_document_by_id(host=host, user=user, password=password, table=table_path, docid=record["assetID"])
            # logger.debug("Found: %s", str(doc))

            if doc is None:
                logger.warning("Asset not found for: %s", record["assetID"])
                failed += 1

            else:
                # lazily get the last part of href - should be the filename
                assetUrl = doc["links"][0]["href"]
                imageFilename = assetUrl.split("/").pop()

                logger.info("Downloading asset for %s", doc['data'][0]['title'])

                newMessage = {
                    "title": doc["data"][0]["title"],
                    "description": doc["data"][0]["description"],
                    "filename": imageFilename,
                    "assetID": doc["_id"],
                }

                # put file to downloadLocation
                response = putfile(
                    host=host,
                    user=user,
                    password=password,
                    file=f"images/{imageFilename}",
                    destfolder=IMAGE_FILE_LOCATION
                )

                if response is not None:
                    logger.debug(
                        "Asset saved in folder %s/%s", HQ_VOLUME_PATH, IMAGE_FILE_LOCATION
                    )

                    # update DB with new location
                    doc["imageDownloadLocation"] = f"{HQ_VOLUME_PATH}/{IMAGE_FILE_LOCATION}/{imageFilename}"

                    if upsert_document(host=host, user=user, password=password, table=table_path, json_dict=doc):
                        logger.debug("Document updated with new location")
                        newMessage['status'] = "success"
                        downloaded += 1

                    else:
                        logger.warning("Failed to update document %s for asset location", doc['_id'])
                        newMessage['status'] = "failed"
                        failed += 1

                    # Publish image saved message to output stream
                    if produce(stream=stream_path, topic=output_topic, record=json.dumps(newMessage)):
                        logger.debug("Published image download event to %s", f"{stream_path}:{output_topic}")
                        # notify ui that we have new message
                        service["count"] += 1
                        # update dashboard with a tile
                        tiles.append(
                            tuple(["Image Download Service", doc['data'][0]['title'], doc['data'][0]['description'], doc["imageDownloadLocation"]])
                        )
                    else:
                        logger.warning("Publish to %s failed for %s", f"{stream_path}:{output_topic}", newMessage)

        except Exception as error:
            logger.warning(error)

    # logger.debug("FINISHED -> OK: %d, FAIL: %d", downloaded, failed)


def asset_broadcast_service():
    """
    Subscribe to IMAGE_DOWNLOAD topic and publish to ASSET_BROADCAST to notify edge clusters for new asset availability
    """

    service = services["assetbroadcast"]

    local_stream_path = f"{HQ_VOLUME_PATH}/{STREAM_PIPELINE}"
    replicated_stream_path = HQ_STREAM_REPLICATED

    input_topic = TOPIC_IMAGE_DOWNLOAD
    output_topic = TOPIC_ASSET_BROADCAST

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        logger.debug("is disabled")

    for msg in consume(stream=local_stream_path, topic=input_topic):
        record = json.loads(msg)
        logger.debug("Received: %s", record['title'])

        # skip assets that failed to download
        if record["status"] == "failed":
            logger.warning("Record has failed, not publishing: %s", record["status"])
            continue

        try:
            # Publish to output topic on the replicated stream
            if produce(
                stream=replicated_stream_path, topic=output_topic, record=json.dumps(record)
            ):
                # update message status
                record["status"] = "broadcast"

                logger.info(
                    "Published asset to %s", f"{replicated_stream_path}:{output_topic}"
                )
                # notify ui that we have new message
                service["count"] += 1
                # update dashboard with a tile
                tiles.append(
                    tuple(["Asset Broadcast Service", f"Broadcasting: {record['assetID']}", record['title'], None])
                )
            else:
                # update message status
                record["status"] = "failed"

                logger.warning(
                    "Publish to %s failed for %s",
                    f"{replicated_stream_path}:{output_topic}",
                    record,
                )

        except Exception as error:
            logger.warning(error)


def asset_response_service(host: str, user: str, password: str):
    """
    Monitor ASSET_REQUEST topic for the requests from Edge
    """

    service = services["assetresponse"]

    stream_path = HQ_STREAM_REPLICATED
    table_path = HQ_IMAGETABLE

    input_topic = TOPIC_ASSET_REQUEST

    service["active"] = True

    # skip if service is disabled by user
    if not service["active"]:
        logger.debug("is disabled")

    try:

        for msg in consume(stream=stream_path, topic=input_topic):
            record = json.loads(msg)
            logger.info("Responding to asset request for: %s", record['title'])

            doc = find_document_by_id(host=host, user=user, password=password, table=table_path, docid=record["assetID"])
            logger.debug("Found: %s", str(doc['data'][0]['title']))

            if doc is None:
                logger.warning("Asset not found for: %s", record['assetID'])

            else:
                logger.info("Copying asset from %s", doc["imageDownloadLocation"])
                filename = basename(doc['imageDownloadLocation'])
                shutil.copyfile(f"/mapr/{HQSite.clustername}{doc['imageDownloadLocation']}", f"/mapr/{HQSite.clustername}{HQ_MISSION_FILES}/{filename}")
                # # FIX: this is the flexible option, doesn't require /mapr mount - but don't want to use async here
                # async for out in run_command(
                #     f"hadoop fs -cp {doc['imageDownloadLocation']} {HQ_MISSION_FILES}"
                # ):
                #     logger.debug(out.strip())


                logger.info("%s sent to mission volume", doc['imageDownloadLocation'])
                # notify ui that we have new message
                service["count"] += 1
                # update dashboard with a tile
                tiles.append(
                    tuple(["Asset Response Service", f"Processing: {record['assetID']}", record['title'], None])
                )
    except Exception as error:
        logger.warning("Error in asset response service: %s", str(error))
