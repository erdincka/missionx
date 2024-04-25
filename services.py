import asyncio
import json
import random
from uuid import uuid4
import importlib_resources
from nicegui import app
from helpers import *


logger = logging.getLogger("services")

# HQ SERVICES

async def nasa_event_service():
    """
    Simulate recieving events from NASA API, send random notification messages every NASA_FEED_INTERVAL seconds to TOPIC_NASAFEED, 
    and save notification message into TABLE
    """

    # reset service counter
    app.storage.user["ui"]["nasaevent"] = 0

    stream_path = f"{HQ_VOLUME_PATH}/{STREAM_LOCAL}"
    table_path = f"{HQ_VOLUME_PATH}/{HQ_IMAGETABLE}"

    # get the items
    input_data = None
    with open(
        importlib_resources.files("app").joinpath(
            NASA_FEED_FILE
        ),
        "r",
    ) as f:
        input_data = json.load(f)

    items = input_data["collection"]["items"]
    output_topic_name = f"{stream_path}:{TOPIC_NASAFEED}"

    while app.storage.general["services"].get("nasaevent", False):
        logger.debug("NASA Event Service is running...")
        count = random.randrange(5)

        # pick "count" random items
        for item in random.sample(items, count):
            # assign a unique ID for table
            item["_id"] = str(uuid4())

            # put message to json table
            response = await run.io_bound(restrunner.dagpost,
                host=app.storage.general["hq"],
                path=f"/api/v2/table/{quote(table_path, safe='')}", 
                json_obj=item
            )

            if response:
                logger.info(
                    "Event notification from NASA: %s",
                    item["data"][0]["title"]
                )

            else:
                logger.warning("Saving event notification failed for %s", item['data'][0]['title'])

            # push message to broadcast stream
            message = {
                "description": "New image event received from NASA.",
                "tablename": table_path.split("/").pop(),
                "assetID": item["_id"],
                "messageCreatorID": "ezshow",
            }

            response = await run.io_bound(restrunner.kafkapost,
                host=app.storage.general["hq"],
                path=f"/topics/{quote(output_topic_name, safe='')}",
                data={"records": [{"value": message}]},
            )

            if response:
                logger.debug("Published image received event to %s", output_topic_name)
                # notify ui that we have new message
                if "nasaevent" in app.storage.user["ui"]:
                    app.storage.user["ui"]["nasaevent"] += 1
            else:
                logger.warning("Publish failed for assetID %s", message['assetID'])

            # add random delay between events (0 to 1 sec)
            await asyncio.sleep(random.random())

        # add delay to publishing
        await asyncio.sleep(NASA_FEED_DELAY)

    # when finished, ensure service is turned off
    app.storage.general["services"]["nasaevent"] = False

