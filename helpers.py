import asyncio
import logging
import re
from types import FunctionType
from nicegui import ui, binding, app

APP_NAME = "missionX"

DEMO = {
    "name": "core to edge",
    "description": "With this demo, we will use Data Fabric to enable our microservice-architecture app to process end to end pipeline across multiple locations.",
    "image": "core-edge.png",
}

HQ_VOLUME_NAME = "missionX"
HQ_VOLUME_PATH = "/apps/missionX"

EDGE_VOLUME_PATH = "/apps"

STREAM_LOCAL = "pipelineStream"
HQ_STREAM_REPLICATED = "replicatedStream"
EDGE_STREAM_REPLICATED = "missionX.replicatedStream"

HQ_IMAGETABLE = "imagesTable"
TOPIC_NASAFEED = "NASAFEED"
TOPIC_IMAGE_DOWNLOAD = "IMAGE_DOWNLOAD"
TOPIC_ASSET_BROADCAST = "ASSET_BROADCAST"
TOPIC_ASSET_REQUEST = "ASSET_REQUEST"
TOPIC_DASHBOARD_UPDATES = "DASHBOARD_MONITOR"
NASA_FEED_FILE = "meta/query_results_combined-USE.json"
IMAGE_FILE_LOCATION = "downloadedAssets"
HQ_MISSION_FILES = "files"
EDGE_MISSION_FILES = "missionX.files"

# timeout stream consumers
MAX_POLL_TIME = 5

# service name & processing delay in tuple
SERVICES = {
    "HQ": [
        ("NASA Feed", 5),
        ("Image Download", 2),
        ("Asset Broadcast", 2),
        ("Asset Response", 2),
    ],
    "EDGE": [
        ("Upstream Comm", 3),
        ("Broadcast Listener", 3),
        ("Asset Request", 3),
        ("Asset Viewer", 3),
    ],
}

logger = logging.getLogger("helpers")


# wrapper to make sync calls async-like
def fire_and_forget(f):
    def wrapped(*args, **kwargs):
        # return asyncio.get_event_loop().run_in_executor(None, f, *args, *[v for v in kwargs.values()])
        return asyncio.new_event_loop().run_in_executor(None, f, *args, *[v for v in kwargs.values()])

    return wrapped

class LogElementHandler(logging.Handler):
    """A logging handler that emits messages to a log element."""

    def __init__(self, element: ui.log, level: int = logging.DEBUG) -> None:
        self.element = element
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.element.push(msg)
        except Exception:
            self.handleError(record)


def configure_logging():
    """
    Set up logging and supress third party errors
    """

    logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s:%(levelname)s:%(name)s (%(funcName)s:%(lineno)d): %(message)s",
                    datefmt='%H:%M:%S')

    # during development
    logger.setLevel(logging.DEBUG)

    # INSECURE REQUESTS ARE OK in Lab
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # reduce logs from these
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logging.getLogger("watchfiles").setLevel(logging.FATAL)

    logging.getLogger("faker").setLevel(logging.FATAL)

    logging.getLogger("pyiceberg.io").setLevel(logging.WARNING)

    logging.getLogger("mapr.ojai.storage.OJAIConnection").setLevel(logging.WARNING)
    logging.getLogger("mapr.ojai.storage.OJAIDocumentStore").setLevel(logging.WARNING)

    # https://sam.hooke.me/note/2023/10/nicegui-binding-propagation-warning/
    binding.MAX_PROPAGATION_TIME = 0.05


# Handle exceptions without UI failure
def gracefully_fail(exc: Exception):
    print("gracefully failing...")
    logger.exception(exc)
    app.storage.user["busy"] = False


def not_implemented():
    ui.notify('Not implemented', type='warning')

def extract_wrapped(decorated):
    closure = (c.cell_contents for c in decorated.__closure__)
    return next((c for c in closure if isinstance(c, FunctionType)), None)
