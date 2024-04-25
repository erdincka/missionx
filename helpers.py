import logging
import re
from nicegui import ui

APP_NAME = "missionX"

DEMO = {
    "name": "core to edge",
    "description": "With this demo, we will use Data Fabric to enable our microservice-architecture app to process end to end pipeline across multiple locations.",
    "image": "core-edge.png",
}

HQ_VOLUME_NAME = "core-to-edge"
EDGE_VOLUME_NAME = "edge-to-core"

HQ_VOLUME_PATH = "/apps/core-to-edge"
EDGE_VOLUME_PATH = "/apps/edge-to-core"

STREAM_LOCAL = "pipelineStream"
HQ_STREAM_REPLICATED = "replicatedStream"
EDGE_STREAM_REPLICATED = "edge-replicatedStream"

HQ_IMAGETABLE = "imagesTable"
TOPIC_NASAFEED = "NASAFEED"
TOPIC_IMAGE_DOWNLOADED = "IMAGE_DOWNLOADED"
TOPIC_ASSET_BROADCAST = "ASSET_BROADCAST"
TOPIC_ASSET_REQUEST = "ASSET_REQUEST"
TOPIC_DASHBOARD_UPDATES = "DASHBOARD_MONITOR"
NASA_FEED_FILE = "meta/query_results_combined-USE.json"
IMAGE_FILE_LOCATION = "downloadedAssets"
HQ_MISSION_FILES = "files-missionX"
EDGE_MISSION_FILES = "edge-files-missionX"
NASA_FEED_DELAY = 5
IMAGE_DOWNLOAD_SERVICE_DELAY = 5
ASSET_BROADCAST_DELAY = 3

SERVICES = {
    "HQ": [
        ("NASA Feed", "rss_feed"),
        ("Image Download", "photo_album"),
        ("Asset Broadcast", "cell_tower"),
        ("Asset Request", "compare_arrows"),
    ],
    "EDGE": [
        ("Audit Listener", "hearing"),
        ("Dashboard Listener", "space_dashboard"),
        ("Image Display", "photo_library"),
    ],
}
