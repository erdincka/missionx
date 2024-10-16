import logging
from typing import Callable
from nicegui import binding

logger = logging.getLogger(__name__)

class Service:
    name: str
    delay: int
    active = binding.BindableProperty()
    count = binding.BindableProperty()

    def __init__(self, _name, _delay):
        self.name = _name
        self.delay = _delay
        self.active = False
        self.count = 0

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

HQSite = {
    "clusterName": "",
    # HQ services
    "services": {
        "imagefeed": Service("IMAGE Feed", 5),
        "imagedownload": Service("Image Download", 2),
        "assetbroadcast": Service("Asset Broadcast", 2),
        "assetresponse": Service("Asset Response", 2)
    },
    # Processing assets
    "assets": [],
    # Dashboard tiles
    "tiles": []
}

EdgeSite = {
    "clusterName": "",
    # Edge services
    "services": {
        "auditlistener": Service("Audit Listener", 3),
        "upstreamcomm": Service("Upstream Comm", 3),
        "broadcastlistener": Service("Broadcast Listener", 3),
        "assetrequest": Service("Asset Request", 3),
        "assetviewer": Service("Asset Viewer", 3)
    },
    "assets": [],
    "tiles": []
}
