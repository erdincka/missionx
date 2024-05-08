from nicegui import ui
import inspect
from functions import *

from helpers import *
from hq_services import asset_broadcast_service, asset_response_service, nasa_feed_service, image_download_service
import steps


def hq_page():
    # HQ Dashboard
    with ui.row().classes("w-full no-wrap place-items-center"):
        ui.label("Core Data Pipeline").classes("text-bold")
        ui.icon("info").tooltip(steps.INTRO)

    with ui.row().classes("w-full no-wrap"):
        # left panel
        with ui.column().classes("w-fit"):
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('Data Feed and Services').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["HQ"]:
                    service_status(svc)

            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('System Metrics').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["HQ"]:
                    service_counter(svc)

            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('Control Panel').props('header').classes('text-bold text-sm bg-primary')
                for svc in SERVICES["HQ"]:
                    service_settings(svc)


        # right panel
        with ui.column().classes("w-full mr-2"):
            with ui.stepper().classes("w-full").props("vertical header-nav") as stepper:
                with ui.step('Data Ingestion'):
                    ui.label(steps.INGESTION)
                    
                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(nasa_feed_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, nasa_feed_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        # ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Data Processing (ETL)'):
                    ui.label(steps.ETL)

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(image_download_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, image_download_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Broadcast'):
                    ui.label(
                        "Now we are ready to know all the field teams that we have new intelligence. We send a message to Asset Broadcast topic, so any/all subscribers can see relevant metadata for that asset."
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(asset_broadcast_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_broadcast_service
                            ),
                        )
                        ui.button('Next', on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step('Request Listener'):
                    ui.label(
                        "We broadcast the assets we've got from the feed. Now we are ready to serve the assets for any fielt team if they request it. For that, we have a listener service that monitors the topic ASSET_REQUEST for any request from the field."
                    )

                    ui.label("Click 'Run' to enable the service")

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(extract_wrapped(asset_response_service))).props("outline")
                        ui.button(
                            "Run",
                            on_click=lambda: asyncio.get_event_loop().run_in_executor(
                                None, asset_response_service
                            ),
                        )
                        ui.button("Next", on_click=stepper.next, color="secondary")
                        ui.button('Back', on_click=stepper.previous, color="none")

                with ui.step("Enable stream replication"):
                    ui.label(
                        "We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ."
                    )

                    with ui.stepper_navigation():
                        ui.button("Show code", on_click=lambda: show_code(stream_replica_setup)).props("outline")
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
