from nicegui import ui
from functions import *

from helpers import *
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
                # manually add setting for tile removal
                with ui.item().classes("text-xs m-1 p-1 border"):
                    with ui.item_section():
                        ui.item_label(f"Keep tiles for (s):").classes("no-wrap")
                        slider = ui.slider(min=5, max=60).bind_value(app.storage.general, "tile_remove")
                    with ui.item_section().props('side'):
                        ui.label().bind_text_from(slider, 'value')
                

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

                # manually add stream replication step (not to run in executor)
                with ui.step("Start replication"):
                    ui.label("We need to establish bi-directional communication between HQ and Edge. Let's first enable the replication of broadcast stream so we can get intelligence data from HQ.")
                    with ui.stepper_navigation():
                        ui.button("Code", on_click=lambda s=step: show_code(stream_replica_setup)).props("outline")
                        ui.button(
                            "Run",
                            on_click=stream_replica_setup,
                        )
                        ui.button('Back', on_click=stepper.previous, color="none")
                        

            # The image display widget to show downloaded assets in real-time
            # with ui.scroll_area().classes("w-full"):
            with ui.grid(columns=4).classes("w-full") as images:
                ui.timer(0.5, lambda: dashboard_tiles(os.environ['MAPR_IP'], "dashboard_hq"))
