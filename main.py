import logging

from nicegui import app, ui
from functions import *
from common import *
from page import *

def app_init():
    pass

# catch-all exceptions
app.on_exception(gracefully_fail)
app.on_disconnect(app_init)

# configure the logging
configure_logging()

logger = logging.getLogger(__name__)

app_init()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title=TITLE,
        dark=None,
        storage_secret=STORAGE_SECRET,
        reload=True,
        port=3000,
    )
