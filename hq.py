from nicegui import ui
import inspect
from functions import *

from helpers import *
from hq_services import asset_broadcast_service, asset_response_service, nasa_feed_service, image_download_service
import steps


def hq_page():
    # HQ Dashboard
    ui.label("HQ Dashboard").classes("text-bold")

    with ui.row().classes("w-full place-items-center sticky top-14 bg-slate-200 dark:bg-slate-800 p-3"):
        ui.label("HQ").classes("text-bold")
        ui.space()
        for svc in SERVICES["HQ"]:
            service_status(svc)
            ui.space()

    ui.label(steps.INTRO).classes("")

    with ui.stepper().classes("w-full").props("vertical") as stepper:
        with ui.step('Data Ingestion'):
            ui.label("Data Ingestion").classes("text-bold")
            ui.label(steps.INGESTION)

            with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                ui.code(inspect.getsource(extract_wrapped(nasa_feed_service))).classes(
                    "w-full"
                )

            ui.label("Click 'Run' to enable the service")

            with ui.stepper_navigation():
                ui.button(
                    "Run",
                    on_click=lambda: asyncio.get_event_loop().run_in_executor(
                        None, nasa_feed_service
                    ),
                )
                ui.button('Next', on_click=stepper.next, color="secondary")
                # ui.button('Back', on_click=stepper.previous, color="none")

        with ui.step('Data Processing (ETL)'):
            ui.label("Data Processing (ETL)").classes("text-bold")

            ui.label(steps.ETL)

            with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                ui.code(inspect.getsource(extract_wrapped(image_download_service))).classes(
                    "w-full"
                )

            ui.label("Click 'Run' to enable the service")

            with ui.stepper_navigation():
                ui.button(
                    "Run",
                    on_click=lambda: asyncio.get_event_loop().run_in_executor(
                        None, image_download_service
                    ),
                )
                ui.button('Next', on_click=stepper.next, color="secondary")
                ui.button('Back', on_click=stepper.previous, color="none")

        with ui.step('Broadcast'):
            ui.label("Broadcast").classes("text-bold")
            ui.label(
                "Now we are ready to know all the field teams that we have new intelligence. We send a message to Asset Broadcast topic, so any/all subscribers can see relevant metadata for that asset."
            )

            with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                ui.code(inspect.getsource(extract_wrapped(asset_broadcast_service))).classes(
                    "w-full"
                )

            ui.label("Click 'Run' to enable the service")

            with ui.stepper_navigation():
                ui.button(
                    "Run",
                    on_click=lambda: asyncio.get_event_loop().run_in_executor(
                        None, asset_broadcast_service
                    ),
                )
                ui.button('Next', on_click=stepper.next, color="secondary")
                ui.button('Back', on_click=stepper.previous, color="none")

        with ui.step('Request Listener'):
            ui.label("Request Listener").classes("text-bold")
            ui.label(
                "We broadcast the assets we've got from the feed. Now we are ready to serve the assets for any fielt team if they request it. For that, we have a listener service that monitors the topic ASSET_REQUEST for any request from the field."
            )

            with ui.expansion("Code", caption="Code to enable service", icon="code").classes("w-full"):
                ui.code(
                    inspect.getsource(extract_wrapped(asset_response_service))
                ).classes("w-full")

            ui.label("Click 'Run' to enable the service")

            with ui.stepper_navigation():
                ui.button(
                    "Run",
                    on_click=lambda: asyncio.get_event_loop().run_in_executor(
                        None, asset_response_service
                    ),
                )
                ui.button("Next", on_click=stepper.next, color="secondary")
                ui.button('Back', on_click=stepper.previous, color="none")

        with ui.step("Enable stream replication"):
            ui.label("Enable stream replication").classes("text-bold")
            ui.label(
                "We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ."
            )

            with ui.expansion(
                "Code", caption="Code to setup replication", icon="code"
            ).classes("w-full"):
                ui.code(inspect.getsource(stream_replica_setup)).classes(
                    "w-full"
                )

            with ui.stepper_navigation():
                ui.button(
                    "Run",
                    on_click=lambda: asyncio.get_event_loop().run_in_executor(
                        None, stream_replica_setup
                    ),
                )
                ui.button("Back", on_click=stepper.previous, color="none")

            ui.label("Now you are ready to proceed with the services used by the Field teams. Proceed to Edge dashboard for the rest of the demo.")

    # The image display widget to show downloaded assets in real-time
    with ui.scroll_area().classes("w-full"):
        with ui.grid(columns=5).classes("p-1") as images:
            ui.timer(0.5, lambda: imageshow(os.environ['MAPR_IP'], "hqimages"))
