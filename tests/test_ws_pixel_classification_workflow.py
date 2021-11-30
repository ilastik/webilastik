# pyright: reportUnusedCallResult=false

import os
from webilastik.features.channelwise_fastfilters import GaussianSmoothing, HessianOfGaussianEigenvalues

from webilastik.ui.workflow.ws_pixel_classification_workflow import RPCPayload
# ensure requests will use the mkcert cert. Requests uses certifi by default, i think
os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
# ensure aiohttp will use the mkcert certts. I don't really know where it otherwise gets its certs from
os.environ["SSL_CERT_DIR"] = "/etc/ssl/certs/"

from pathlib import Path
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
from webilastik.datasource import SkimageDataSource
from webilastik.utility.url import Url
from webilastik.libebrains.user_token import UserToken
from webilastik.server import EbrainsSession


finished = False

async def read_server_status(websocket: ClientWebSocketResponse):
    async for message in websocket:
        print(f"Server status update: {message.data}")
        if finished:
            break

async def main():
    ds = SkimageDataSource(filesystem=HttpFs(read_url=Url.parse("https://app.ilastik.org/")), path=Path("api/images/c_cells_1.png"))

    async with aiohttp.ClientSession(
        cookies={EbrainsSession.AUTH_COOKIE_KEY: UserToken.from_environment().access_token}
    ) as session:
        print(f"Creating new session--------------")
        async with session.post(f"https://app.ilastik.org/api/session", json={"session_duration": 30}) as response:
            response.raise_for_status()
            session_data : Dict[str, Any] = await response.json()
            session_id = session_data["id"]
        print(f"Done creating session: {json.dumps(session_data)} <<<<<<<<<<<<<<<<<<")

        for _ in range(10):
            response = await session.get(f"https://app.ilastik.org/api/session/{session_id}")
            response.raise_for_status()
            session_status = await response.json()
            if session_status["status"] == "ready":
                session_url = session_status["url"]
                break
            print(f"Session {session_id} is notready yet")
            _ = await asyncio.sleep(2)
        else:
            raise RuntimeError("Given up waiting on session")

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


            from base64 import b64encode
            encoded_ds: str = b64encode(json.dumps(ds.to_json_value()).encode("utf8"), altchars=b'-_').decode("utf8")

            response_tasks = {}
            for tile in ds.roi.get_tiles(tile_shape=Shape5D(x=256, y=256, c=2), tiles_origin=Point5D.zero()):
                url = f"{session_url}/predictions/raw_data={encoded_ds}/run_id=123456/data/{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_0-1"
                print(f"---> Requesting {url}")
                response_tasks[tile] = session.get(url)

            for tile, resp in response_tasks.items():
                async with resp as response:
                    print("Status:", response.status)
                    print("Content-type:", response.headers['content-type'])

                    if response.status // 100 != 2:
                        raise Exception(f"Error: {(await response.content.read()).decode('utf8')}")

                    tile_bytes = await response.content.read()
                    print(f"Got predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

                    raw_data = np.frombuffer(tile_bytes, dtype=np.uint8).reshape(2, tile.shape.y, tile.shape.x)
                    a = Array5D(raw_data, axiskeys="cyx")
                    # a.show_channels()

            import time

            url = f"{session_url}/export"
            print(f"---> Scheduling a job at {url}:")
            await ws.send_json(RPCPayload(
                applet_name="export_applet",
                method_name="start_export_job",
                arguments={
                    "raw_data_params": {
                        "url": "https://app.ilastik.org/api/images/c_cells_1.png",
                    },
                    "bucket_name": "hbp-image-service",
                    "prefix": f"job_output_{int(time.time())}.precomputed",
                }
            ).to_json_value())
            print(f"---> Job successfully scheduled?")

        global finished;
        finished = True



asyncio.run(main())
