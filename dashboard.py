import logging
from nicegui import binding

logger = logging.getLogger(__name__)

class Services:
    imagefeed = binding.BindableProperty()

    def __init__(self):
        self.services = {}

class Dashboard:
    assets = binding.BindableProperty()
    messages = binding.BindableProperty()
    imagefeed_delay = binding.BindableProperty()
    imagedownload_delay = binding.BindableProperty()
    assetbroadcast_delay = binding.BindableProperty()
    assetresponse_delay = binding.BindableProperty()
    auditlistener_delay = binding.BindableProperty()
    upstreamcomm_delay = binding.BindableProperty()
    broadcastlistener_delay = binding.BindableProperty()
    assetrequest_delay = binding.BindableProperty()
    assetviewer_delay = binding.BindableProperty()

    def __init__(self):
        self.assets = [] # collection of assets
        self.messages = [] # messages sent to dashboard
        # HQ services
        self.imagefeed_delay = 5
        self.imagedownload_delay = 2
        self.assetbroadcast_delay = 2
        self.assetresponse_delay = 2
        # Edge services
        self.auditlistener_delay = 3
        self.upstreamcomm_delay = 3
        self.broadcastlistener_delay = 3
        self.assetrequest_delay = 3
        self.assetviewer_delay = 3
