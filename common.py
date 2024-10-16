
APP_NAME = "missionX"
TITLE = "Data Fabric Core to Edge Demo"
STORAGE_SECRET = "ezmer@1r0cks"

DEMO = {
    "name": "core to edge",
    "description": "With this demo, we will use Data Fabric to enable our microservice-architecture app to process end to end pipeline across multiple locations.",
    "image": "core-edge.png",
    "link": "https://github.com/erdincka/missionx"
}

MOUNT_PATH = "/mapr"

HQ_VOLUME_PATH = "/apps/missionX"

EDGE_VOLUME_PATH = "/apps/missionX-edge"

STREAM_PIPELINE = "pipelineStream"
HQ_STREAM_REPLICATED = f"{HQ_VOLUME_PATH}/replicatedStream"
EDGE_STREAM_REPLICATED = f"{EDGE_VOLUME_PATH}/replicatedStream.copy"

HQ_IMAGETABLE = f"{HQ_VOLUME_PATH}/imagesTable"
TOPIC_IMAGEFEED = "IMAGEFEED"
TOPIC_IMAGE_DOWNLOAD = "IMAGE_DOWNLOAD"
TOPIC_ASSET_BROADCAST = "ASSET_BROADCAST"
TOPIC_ASSET_REQUEST = "ASSET_REQUEST"
TOPIC_DASHBOARD_UPDATES = "DASHBOARD_MONITOR"
IMAGE_FEED_FILE = "meta/query_results_combined-USE.json"
IMAGE_FILE_LOCATION = "downloadedAssets"
HQ_MISSION_FILES = f"{HQ_VOLUME_PATH}/files"
EDGE_MISSION_FILES = f"{EDGE_VOLUME_PATH}/files.mirror"

# timeout stream consumers
MAX_POLL_TIME = 5

HQ = "HQ"
EDGE = "EDGE"

# service name & processing delay in tuple
# SERVICES = {
#     "HQ": [
#         ("IMAGE Feed", 5),
#         ("Image Download", 2),
#         ("Asset Broadcast", 2),
#         ("Asset Response", 2),
#     ],
#     "EDGE": [
#         ("Audit Listener", 3),
#         ("Upstream Comm", 3),
#         ("Broadcast Listener", 3),
#         ("Asset Request", 3),
#         ("Asset Viewer", 3),
#     ],
# }

BGCOLORS = {
    "IMAGE Feed Service": "bg-sky-300",
    "Image Download Service": "bg-red-300",
    "Asset Broadcast Service": "bg-green-300",
    "Asset Response Service": "bg-orange-300",
    "Upstream Comm Service": "bg-amber-300",
    "Broadcast Listener Service": "bg-emerald-300",
    "Asset Request Service": "bg-lime-300",
    "Asset Viewer Service": "bg-stone-300",
}


cluster_configuration_steps = [
    {
        "name": "clusterinfo",
        "info": "Get cluster details",
        "status": "pending",
    },
    {
        "name": "reconfigure",
        "info": "Configure cluster",
        "status": "pending",
    },
    {
        "name": "createvolumes",
        "info": "Create application volumes and streams",
        "status": "pending",
    },
    {
        "name": "auditing",
        "info": "Enable auditing for cluster and data operations",
        "status": "pending",
    }
]
