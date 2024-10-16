from nicegui import ui
from sites import *
import edge
from functions import *

from helpers import *
from common import *
from hq_services import *
import steps

services = HQSite['services']
tiles = HQSite['tiles']
assets = HQSite['assets']

logger = logging.getLogger(__name__)

@ui.page("/hq_dashboard", title="HQ Dashboard")
def hq_page():
    HQSite['clusterName'] = get_cluster_name(HQ)
    # HQ Services
    imagefeed_timer = ui.timer(services['imagefeed'].delay,
                               lambda: run.io_bound(image_feed_service,
                                            host=app.storage.user['HQ_HOST'],
                                            user=app.storage.user['MAPR_USER'],
                                            password=app.storage.user['MAPR_PASS']),
                                active=False)
    imagedownload_timer = ui.timer(services['imagedownload'].delay,
                                   lambda: run.io_bound(image_download_service,
                                            host=app.storage.user['HQ_HOST'],
                                            user=app.storage.user['MAPR_USER'],
                                            password=app.storage.user['MAPR_PASS']),
                                    active=False)
    assetbroadcast_timer = ui.timer(services['assetbroadcast'].delay,
                                    lambda: run.io_bound(asset_broadcast_service),
                                    active=False)
    assetresponse_timer = ui.timer(services['assetresponse'].delay,
                                   lambda: run.io_bound(asset_response_service,
                                            host=app.storage.user['HQ_HOST'],
                                            user=app.storage.user['MAPR_USER'],
                                            password=app.storage.user['MAPR_PASS']),
                                    active=False)

    # HQ Dashboard
    with ui.row().classes("w-full no-wrap place-items-center"):
        ui.label("HQ Dashboard").classes("text-bold")
        ui.icon("info").tooltip(steps.INTRO)

        ui.space()
        # for svc in SERVICES[HQ]:
        #     service_status(svc)
        ui.switch('Image Feed').bind_value_to(imagefeed_timer, 'active')
        ui.switch('Image Download').bind_value_to(imagedownload_timer, 'active')
        ui.switch('Asset Broadcast').bind_value_to(assetbroadcast_timer, 'active')
        ui.switch('Asset Response').bind_value_to(assetresponse_timer, 'active')

        ui.space()
        ui.button("Open Edge Dashboard", on_click=lambda: ui.navigate.to(edge.edge_page, new_tab=True))

    with ui.row().classes("w-full no-wrap"):
        # left panel
        with ui.column().classes("w-fit"):
            # Metrics
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                ui.item_label('System Metrics').props('header').classes('text-bold text-sm bg-primary')
                for service in services.items():
                    service_counter(service)

            # Control Panel
            with ui.list().props('bordered separator').classes("text-xs w-full"):
                # ui.item_label('Control Panel').props('header').classes('text-bold text-sm bg-primary')
                # for service in services.items():
                #     service_settings(service)
                # # manually add setting for tile removal
                with ui.item().classes("text-xs m-1 p-1 border"):
                    with ui.item_section():
                        ui.item_label(f"Keep tiles for (s):").classes("no-wrap")
                        slider = ui.slider(min=5, max=60).bind_value(app.storage.general, "tile_remove")
                    with ui.item_section().props('side'):
                        ui.label().bind_text_from(slider, 'value')

        # right panel
        with ui.column().classes("w-full"):
            ui.label("").bind_text_from(services['imagefeed'], "delay")
            ui.label("").bind_text_from(services['imagefeed'], "count")
            with ui.grid(columns=5).classes("w-full"):
                # The image display widget to show downloaded assets in real-time
                ui.timer(0.2, lambda: dashboard_tiles(app.storage.user["HQ_HOST"], tiles))
                # update metrics
                # ui.timer(0.5, lambda: update_metrics_for(HQ, metric_chart))
