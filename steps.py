from hq_services import *
from edge_services import *


INTRO = """
HQ acts as the hub for information flow in this scenario. It is where the data is collected from various sources (we simulate IMAGE feed),
processed and distributed to various targets, including the field teams working at the edge, as actionable intelligence.
Microservice status for Headquarters are shown above.
You can pause/resume them on clicking their icon. The numbers indicate the processed items for each service.
We are going to start and explain each service in the following steps.
"""

FLOW = {
    HQ: [
        {
            "title": "Data Ingestion Service",
            "description": """
Let's start with generating sample data mocking RSS feed from NASA Image API.
We are using pre-recorded images from 2014, but we can also get them in real-time using the relevant NASA API calls.
For each message we recieve, we will create a record in the JSON Table and
send a message to the pipeline to inform the next service, Image Download, so it can process the message content.
""",
            "code": image_feed_service,
        },
        {
            "title": "Data Processing (ETL) Service",
            "description": """
With each message in the pipeline, we will get a link to download the asset. We will download this asset,
and save the image in a volume, while updating the location of the asset in the database.
""",
            "code": image_download_service,
        },
        {
            "title": "Broadcast Service",
            "description": "Now we are ready to know all the field teams that we have new intelligence. We send a message to Asset Broadcast topic, so any/all subscribers can see relevant metadata for that asset.",
            "code": asset_broadcast_service,
        },
        {
            "title": "Request Listener",
            "description": "We broadcast the assets we've got from the feed. Now we are ready to serve the assets for any field team if they request it. For that, we have a listener service that monitors the topic ASSET_REQUEST for any request from the field.",
            "code": asset_response_service,
        },
    ],
    EDGE: [
        {
            "title": "Upstream Comm",
            "description": "Monitor upstream connectivity and data replication status",
            "code": upstream_comm_service,
        },
        {
            "title": "Broadcast Listener",
            "description": "We will subscribe to the ASSET_BROADCAST topic so we can be notified of incoming new assets.",
            "code": broadcast_listener_service,
        },
        {
            "title": "Asset Request",
            "description": """Any assets requested by clicking on the asset data will be put into ASSET_REQUEST topic,
            so HQ can process and send the asset through the replicated volume.""",
            "code": asset_request_service,
        },
        {
            "title": "Asset Viewer",
            "description": """We will periodically check the volume where the requested assets are copied. Once the asset is ready, it will be
            displayed in a tile on the Dashboard.""",
            "code": asset_viewer_service,
        },
    ]
}
