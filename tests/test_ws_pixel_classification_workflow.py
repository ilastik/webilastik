# pyright: reportUnusedCallResult=false

import os
import sys
from webilastik.config import EbrainsUserCredentialsConfig

from webilastik.server.rpc.dto import AddPixelAnnotationParams, StartPixelProbabilitiesExportJobParamsDto, StartSimpleSegmentationExportJobParamsDto
# ensure requests will use the mkcert cert. Requests uses certifi by default, i think
os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
# ensure aiohttp will use the mkcert certts. I don't really know where it otherwise gets its certs from
os.environ["SSL_CERT_DIR"] = "/etc/ssl/certs/"

from pathlib import PurePosixPath
import aiohttp
import asyncio
import json
from typing import Dict, Any


import numpy as np
from aiohttp.client_ws import ClientWebSocketResponse


from tests import SkipException, create_precomputed_chunks_sink, get_sample_c_cells_pixel_annotations, get_sample_feature_extractors, get_test_output_bucket_fs
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.filesystem.bucket_fs import BucketFs
from webilastik.ui.datasource import try_get_datasources_from_url
from webilastik.ui.workflow.ws_pixel_classification_workflow import RPCPayload
from webilastik.utility.url import Url
from webilastik.libebrains.user_token import UserToken
from webilastik.server.session_allocator import EbrainsLogin


finished = False
classifier_generation = 0

async def read_server_status(websocket: ClientWebSocketResponse):
    global classifier_generation
    async for message in websocket:
        parsed_message = message.json()
        # print(f"workflow state: {json.dumps(parsed_message)}")


        if "error" in parsed_message:
            print(f"error state: {json.dumps(parsed_message['error'], indent=4)}")
        if "export_applet" in parsed_message:
            print(f"export_applet state: {json.dumps(parsed_message['export_applet'], indent=4)}")
        if "pixel_classification_applet" in parsed_message:
            classifier_generation = parsed_message["pixel_classification_applet"]["generation"]
        if finished:
            break

async def main():
    ilastik_root_url = Url.parse("https://app.ilastik.org/")
    assert ilastik_root_url is not None
    data_url = Url.parse("precomputed://https://app.ilastik.org/public/images/c_cells_2.precomputed")
    assert data_url is not None
    datasources = try_get_datasources_from_url(url=data_url, ebrains_user_credentials=None)
    if isinstance(datasources, Exception):
        raise datasources
    assert isinstance(datasources, tuple)
    ds = datasources[0]
    token = EbrainsUserCredentialsConfig.try_get()
    if isinstance(token, (type(None), Exception)):
        print(f"No ebrains token. Skipping", file=sys.stderr)
        exit(0)
    assert isinstance(token, UserToken)

    async with aiohttp.ClientSession(
        cookies={"ebrains_user_access_token": token.access_token}
    ) as session:
        print(f"Creating new session--------------")
        async with session.post(ilastik_root_url.concatpath("api/session").raw, json={"session_duration_minutes": 15}) as response:
            response.raise_for_status()
            session_data : Dict[str, Any] = await response.json()
            session_id = session_data["id"]
        print(f"Done creating session: {json.dumps(session_data)} <<<<<<<<<<<<<<<<<<")

        for _ in range(10):
            response = await session.get(ilastik_root_url.concatpath(f"api/session/{session_id}").raw)
            response.raise_for_status()
            session_status = await response.json()
            if session_status["status"] == "ready":
                session_url = session_status["url"]
                break
            print(f"Session {session_id} is notready yet")
            _ = await asyncio.sleep(2)
        else:
            raise RuntimeError("Given up waiting on session")

        # exit(1)

        async with session.ws_connect(f"{session_url}/ws") as ws:
            _ = asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending some feature extractors=======")
            await ws.send_json(
                RPCPayload(
                    applet_name="feature_selection_applet",
                    method_name="add_feature_extractors",
                    arguments={
                        "feature_extractors": tuple(fe.to_dto().to_json_value() for fe in get_sample_feature_extractors())
                    }
                ).to_json_value()
            )
            print("done sending feature extractors<<<<<")

            print("sending some annotations=======")
            default_label_names = ["Foreground", "Background"]
            labels = get_sample_c_cells_pixel_annotations(override_datasource=ds)
            for label_name, label in zip(default_label_names, labels):
                for a in label.annotations:
                    await ws.send_json(
                        RPCPayload(
                            applet_name="brushing_applet",
                            method_name="add_annotation",
                            arguments=AddPixelAnnotationParams(
                                label_name=label_name,
                                pixel_annotation=a.to_dto(),
                            ).to_json_value()
                        ).to_json_value()
                    )

            print("done sending annotations<<<<<")
            await asyncio.sleep(2)

            print("Enabling live update=======")
            await ws.send_json(
                RPCPayload(
                    applet_name="pixel_classification_applet",
                    method_name="set_live_update",
                    arguments={
                        "live_update": True
                    }
                ).to_json_value()
            )
            await asyncio.sleep(2)


            # from base64 import b64encode
            # encoded_ds: str = b64encode(json.dumps(ds.to_json_value()).encode("utf8"), altchars=b'-_').decode("utf8")

            # response_tasks = {}
            # for tile in ds.roi.get_tiles(tile_shape=Shape5D(x=256, y=256, c=2), tiles_origin=Point5D.zero()):
            #     url = f"{session_url}/predictions/raw_data={encoded_ds}/generation={classifier_generation}/data/{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_0-1"
            #     print(f"---> Requesting {url}")
            #     response_tasks[tile] = session.get(url)

            # for tile, resp in response_tasks.items():
            #     async with resp as response:
            #         print("Status:", response.status)
            #         print("Content-type:", response.headers['content-type'])

            #         if response.status // 100 != 2:
            #             raise Exception(f"Error: {(await response.content.read()).decode('utf8')}")

            #         tile_bytes = await response.content.read()
            #         print(f"Got predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

            #         raw_data = np.frombuffer(tile_bytes, dtype=np.uint8).reshape(2, tile.shape.y, tile.shape.x)
            #         Array5D(raw_data, axiskeys="cyx").show_channels()

            predictions_export_datasink = create_precomputed_chunks_sink(
                shape=ds.shape.updated(c=2),
                dtype=np.dtype("float32"),
                chunk_size=ds.tile_shape.updated(c=2),
                name="predictions_export_datasink.precomputed",
                fs=get_test_output_bucket_fs(),
            )

            print(f"Sending predictions job request??????")
            await ws.send_json(
                RPCPayload(
                    applet_name="export_applet",
                    method_name="start_export_job",
                    arguments=StartPixelProbabilitiesExportJobParamsDto(
                        datasource=ds.to_dto(),
                        datasink=predictions_export_datasink.to_dto(),
                    ).to_json_value()
                ).to_json_value()
            )


            simple_segmentation_datasink = create_precomputed_chunks_sink(
                shape=ds.shape.updated(c=3),
                dtype=np.dtype("uint8"),
                chunk_size=ds.tile_shape.updated(c=3),
                name="predictions_export_datasink.precomputed",
                fs=get_test_output_bucket_fs(),
            )

            print(f"Sending simple segmentation job request??????")
            await ws.send_json(
                RPCPayload(
                    applet_name="export_applet",
                    method_name="start_simple_segmentation_export_job",
                    arguments=StartSimpleSegmentationExportJobParamsDto(
                        label_header=labels[0].to_header_message.to_dto(),
                        datasource=ds.to_dto(),
                        datasink=simple_segmentation_datasink.to_dto(),
                    ).to_json_value()
                ).to_json_value()
            )



            print(f"---> Job successfully scheduled? Waiting for a while")
            await asyncio.sleep(15)
            print(f"Done waiting. Checking outputs")

            predictions_output = predictions_export_datasink.to_datasource()
            for tile in predictions_output.roi.get_datasource_tiles():
                tile.retrieve().as_uint8(normalized=True)#.show_channels()

            segmentation_output_1 = simple_segmentation_datasink.to_datasource()
            for tile in segmentation_output_1.roi.get_datasource_tiles():
                tile.retrieve()#.show_images()


            close_url = f"{session_url}/close"
            print(f"Closing session py sending delete to {close_url}")
            r = await session.delete(close_url)
            r.raise_for_status()

        global finished;
        finished = True



asyncio.run(main())
