# pyright: reportUnusedCallResult=false

import os
from sys import prefix
from tests import create_precomputed_chunks_sink
from webilastik.datasource.precomputed_chunks_datasource import PrecomputedChunksDataSource
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues
from webilastik.filesystem.bucket_fs import BucketFs

from webilastik.ui.workflow.ws_pixel_classification_workflow import RPCPayload
from webilastik.utility import get_now_string
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
from ndstructs.point5D import Shape5D, Point5D
from ndstructs.array5D import Array5D

from webilastik.annotations import Annotation, Color
from webilastik.filesystem.http_fs import HttpFs
from webilastik.datasource.skimage_datasource import SkimageDataSource
from webilastik.utility.url import Url
from webilastik.libebrains.user_token import UserToken
from webilastik.server.session_allocator import EbrainsSession


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
    ds = SkimageDataSource(filesystem=HttpFs(read_url=ilastik_root_url), path=PurePosixPath("public/images/c_cells_1.png"))
    token = UserToken.from_environment()
    assert isinstance(token, UserToken)

    async with aiohttp.ClientSession(
        cookies={EbrainsSession.AUTH_COOKIE_KEY: token.access_token}
    ) as session:
        print(f"Creating new session--------------")
        async with session.post(ilastik_root_url.concatpath("api/session").raw, json={"session_duration": 60 * 15}) as response:
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
                        "feature_extractors": tuple([
                            GaussianSmoothing(sigma=0.3, axis_2d="z").to_json_data(),
                            HessianOfGaussianEigenvalues(scale=0.7, axis_2d="z").to_json_data(),
                        ])
                    }
                ).to_json_value()
            )
            print("done sending feature extractors<<<<<")

            print("sending some annotations=======")
            green = Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0))
            red = Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0))
            brush_strokes = [
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
                    color=green,
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                    color=green,
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
                    color=red,
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
                    color=red,
                    raw_data=ds
                ),
            ]
            await ws.send_json(
                RPCPayload(
                    applet_name="brushing_applet",
                    method_name="add_annotations",
                    arguments={
                        "annotations": tuple(a.to_json_data() for a in brush_strokes)
                    }
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

            hbp_image_service_bucket_fs = BucketFs(
                    bucket_name="hbp-image-service",
                    ebrains_user_token=UserToken.get_global_token_or_raise(),
                    prefix=PurePosixPath("/"),
                )


            predictions_export_datasink = create_precomputed_chunks_sink(
                shape=ds.shape.updated(c=2),
                dtype=np.dtype("float32"),
                chunk_size=ds.tile_shape,
                bucket_fs=hbp_image_service_bucket_fs
            )

            print(f"Sending predictions job request??????")
            await ws.send_json(
                RPCPayload(
                    applet_name="export_applet",
                    method_name="start_export_job",
                    arguments={
                        "datasource": ds.to_json_value(),
                        "datasink": predictions_export_datasink.to_json_value(),
                    }
                ).to_json_value()
            )


            simple_segmentation_datasinks = [
                create_precomputed_chunks_sink(
                    shape=ds.shape.updated(c=3),
                    dtype=np.dtype("uint8"),
                    chunk_size=ds.tile_shape.updated(c=3),
                    bucket_fs=hbp_image_service_bucket_fs
                ),
                create_precomputed_chunks_sink(
                    shape=ds.shape.updated(c=3),
                    dtype=np.dtype("uint8"),
                    chunk_size=ds.tile_shape.updated(c=3),
                    bucket_fs=hbp_image_service_bucket_fs
                ),
            ]

            print(f"Sending simpoe segmentation job request??????")
            await ws.send_json(
                RPCPayload(
                    applet_name="export_applet",
                    method_name="start_simple_segmentation_export_job",
                    arguments={
                        "datasource": ds.to_json_value(),
                        "datasinks": tuple(ds.to_json_value() for ds in simple_segmentation_datasinks),
                    }
                ).to_json_value()
            )



            print(f"---> Job successfully scheduled? Waiting for a while")
            await asyncio.sleep(15)
            print(f"Done waiting. Checking outputs")

            predictions_output = PrecomputedChunksDataSource(
                filesystem=hbp_image_service_bucket_fs,
                path=predictions_export_datasink.path,
                resolution=(1,1,1)
            )
            for tile in predictions_output.roi.get_datasource_tiles():
                tile.retrieve().as_uint8(normalized=True).show_channels()

            segmentation_output_1 = PrecomputedChunksDataSource(
                filesystem=hbp_image_service_bucket_fs,
                path=simple_segmentation_datasinks[1].path,
                resolution=(1,1,1)
            )
            for tile in segmentation_output_1.roi.get_datasource_tiles():
                tile.retrieve().show_images()


            close_url = f"{session_url}/close"
            print(f"Closing session py sending delete to {close_url}")
            r = await session.delete(close_url)
            r.raise_for_status()

        global finished;
        finished = True



asyncio.run(main())
