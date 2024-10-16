import logging
from nicegui import ui, binding, app

logger = logging.getLogger(__name__)


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
                    format="%(asctime)s:%(levelname)s %(filename)s:%(lineno)d (%(funcName)s): %(message)s",
                    datefmt='%H:%M:%S')

    # during development
    logger.setLevel(logging.DEBUG)

    # INSECURE REQUESTS ARE OK in Lab
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # reduce logs from these
    logging.getLogger("streams_handle_rd_kafka_assign").setLevel(logging.FATAL)
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


def not_implemented():
    ui.notify('Not implemented', type='warning')

# def extract_wrapped(decorated):
#     closure = (c.cell_contents for c in decorated.__closure__)
#     return next((c for c in closure if isinstance(c, FunctionType)), None)

def logging_card():
    # Realtime logging
    with ui.card().bind_visibility_from(app.storage.user, 'demo_mode').props("flat") as logging_card:
        # ui.label("App log").classes("uppercase")
        log = ui.log().classes("h-24")
        handler = LogElementHandler(log, logging.INFO)
        rootLogger = logging.getLogger()
        rootLogger.addHandler(handler)
        ui.context.client.on_disconnect(lambda: rootLogger.removeHandler(handler))
        rootLogger.info("Logging started")

    return logging_card
