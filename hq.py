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
                for step in steps.FLOW["HQ"]:
                    with ui.step(step.get('title',"")):
                        ui.label(step.get('description', ""))
                        with ui.stepper_navigation():
                            ui.button("Code", on_click=lambda s=step: show_code(s.get("code", ""))).props("outline")
                            ui.button(
                                "Start",
                                on_click=lambda s=step: asyncio.get_event_loop().run_in_executor(
                                    None, s.get("function", None)
                                ),
                            )
                            ui.button('Next', on_click=stepper.next, color="secondary")
                            ui.button('Back', on_click=stepper.previous, color="none")


            ui.label("Now you are ready to proceed with the services used by the Field teams. Proceed to Edge dashboard for the rest of the demo.")

            # The image display widget to show downloaded assets in real-time
            with ui.scroll_area().classes("w-full"):
                with ui.grid(columns=5).classes("p-1") as images:
                    ui.timer(0.5, lambda: imageshow(os.environ['MAPR_IP'], "hqimages"))
