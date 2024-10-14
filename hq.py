from nicegui import ui
import edge
from functions import *

from helpers import *
from common import *
from hq_services import asset_broadcast_service, asset_response_service, image_download_service, nasa_feed_service
import steps

logger = logging.getLogger(__name__)

@ui.page("/hq_dashboard", title="HQ Dashboard")
def hq_page():
    # HQ Services
    nasafeed_timer = ui.timer(app.storage.general["nasafeed_delay"], lambda: run.io_bound(nasa_feed_service, host=app.storage.user['HQ_HOST'], user=app.storage.user['MAPR_USER'], password=app.storage.user['MAPR_PASS']), active=False)
    imagedownload_timer = ui.timer(app.storage.general["imagedownload_delay"], lambda: run.io_bound(image_download_service, host=app.storage.user['HQ_HOST'], user=app.storage.user['MAPR_USER'], password=app.storage.user['MAPR_PASS']), active=False)
    assetbroadcast_timer = ui.timer(app.storage.general["assetbroadcast_delay"], lambda: run.io_bound(asset_broadcast_service), active=False)
    assetresponse_timer = ui.timer(app.storage.general["assetresponse_delay"], lambda: run.io_bound(asset_response_service, host=app.storage.user['HQ_HOST'], user=app.storage.user['MAPR_USER'], password=app.storage.user['MAPR_PASS']), active=False)

    # HQ Dashboard
    with ui.row().classes("w-full no-wrap place-items-center"):
        ui.label("HQ Dashboard").classes("text-bold")
        ui.icon("info").tooltip(steps.INTRO)

        ui.space()
        # for svc in SERVICES["HQ"]:
        #     service_status(svc)
        ui.switch('NASA Feed').bind_value_to(nasafeed_timer, 'active')
        ui.switch('Image Download').bind_value_to(imagedownload_timer, 'active')
        ui.switch('Asset Broadcast').bind_value_to(assetbroadcast_timer, 'active')
        ui.switch('Asset Response').bind_value_to(assetresponse_timer, 'active')

        ui.space()
        ui.button("Open Edge Dashboard", on_click=lambda: ui.navigate.to(edge.edge_page, new_tab=True))

    with ui.row().classes("w-full no-wrap"):
        # left panel
        # with ui.column().classes("w-fit"):
            # with ui.list().props('bordered separator').classes("text-xs w-full"):
            #     ui.item_label('System Metrics').props('header').classes('text-bold text-sm bg-primary')
            # for svc in SERVICES["HQ"]:
            #     service_counter(svc)

            # with ui.list().props('bordered separator').classes("text-xs w-full"):
            #     ui.item_label('Control Panel').props('header').classes('text-bold text-sm bg-primary')
            #     for svc in SERVICES["HQ"]:
            #         service_settings(svc)
            #     # manually add setting for tile removal
            #     with ui.item().classes("text-xs m-1 p-1 border"):
            #         with ui.item_section():
            #             ui.item_label(f"Keep tiles for (s):").classes("no-wrap")
            #             slider = ui.slider(min=5, max=60).bind_value(app.storage.general, "tile_remove")
            #         with ui.item_section().props('side'):
            #             ui.label().bind_text_from(slider, 'value')


        # right panel
        # with ui.column().classes("w-full mr-2"):
            gaugeData = []
            option = {
                'series': [
                    {
                        'type': 'gauge',
                        'startAngle': 90,
                        'endAngle': -270,
                        'pointer': {
                            'show': False
                        },
                        'progress': {
                            'show': True,
                            'overlap': False,
                            'roundCap': True,
                            'clip': False,
                            'itemStyle': {
                                'borderWidth': 1,
                                'borderColor': '#464646'
                            }
                        },
                        'axisLine': {
                            'lineStyle': {
                                'width': 20
                            }
                        },
                        'splitLine': {
                            'show': False,
                            'distance': 0,
                            'length': 10
                        },
                        'axisTick': {
                            'show': False
                        },
                        'axisLabel': {
                            'show': False,
                            'distance': 5
                        },
                        'data': gaugeData,
                        'title': {
                            'fontSize': 10
                        },
                        'detail': {
                            'width': 15,
                            'height': 10,
                            'fontSize': 10,
                            'color': 'inherit',
                            'borderColor': 'inherit',
                            'borderRadius': 10,
                            'borderWidth': 1,
                        }
                    }
                ]
            }

            with ui.grid(columns=5).classes("w-full"):
                mychart = ui.echart(options=option)
                # The image display widget to show downloaded assets in real-time
                ui.timer(0.2, lambda: dashboard_tiles(app.storage.user["HQ_HOST"], "dashboard_hq"))
                # update metrics
                ui.timer(0.5, lambda: update_metrics_for("HQ", mychart))


#### OLD GAUGE
            # option = {
            #     'series': [
            #         {
            #             'type': 'gauge',
            #             'anchor': {
            #                 'show': True,
            #                 'size': 14,
            #                 'itemStyle': {
            #                     'color': '#FAC858'
            #                 }
            #             },
            #             'pointer': {
            #                 'icon': 'path://M2.9,0.7L2.9,0.7c1.4,0,2.6,1.2,2.6,2.6v115c0,1.4-1.2,2.6-2.6,2.6l0,0c-1.4,0-2.6-1.2-2.6-2.6V3.3C0.3,1.9,1.4,0.7,2.9,0.7z',
            #                 'width': 8,
            #                 'length': '80%',
            #                 'offsetCenter': [0, '8%']
            #             },
            #             'progress': {
            #                 'show': True,
            #                 'overlap': True,
            #                 'roundCap': True
            #             },
            #             'axisLine': {
            #                 'roundCap': True
            #             },
            #             'data': gaugeData,
            #             'title': {
            #                 'fontSize': 9
            #             },
            #             'detail': {
            #                 'width': 20,
            #                 'height': 10,
            #                 'fontSize': 9,
            #                 'color': 'inherit',
            #                 'borderColor': 'inherit',
            #                 'borderRadius': 3,
            #                 'borderWidth': 1
            #             }
            #         }
            #     ]
            # }
