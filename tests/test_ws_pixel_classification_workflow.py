from ndstructs.datasource.DataSource import DataSource
from webilastik.annotations import annotation
import aiohttp
import asyncio
import json
from aiohttp.client_ws import ClientWebSocketResponse
from ndstructs.point5D import Interval5D, Shape5D
import numpy as np
import uuid
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ndstructs import Array5D, Point5D
from webilastik.annotations import Annotation, Color
from webilastik.datasource import datasource_from_url

finished = False

async def read_server_status(websocket: ClientWebSocketResponse):
    async for message in websocket:
        print(f"Server status update: {message.data}")
        if finished:
            break

async def main():
    ds = datasource_from_url("http://localhost:8000/cropped1.png")

    async with aiohttp.ClientSession() as session:

        print(f"Creating new session--------------")
        async with session.post(f"http://localhost:5000/session", json={"session_duration": 30}) as response:
            response.raise_for_status()
            session_data : Dict[str, Any] = await response.json()
            session_id = session_data["id"]
        print(f"Done creating session: {json.dumps(session_data)} <<<<<<<<<<<<<<<<<<")

        session_is_ready = False
        for _ in range(10):
            response = await session.get(f"http://localhost:5000/session/{session_id}")
            response.raise_for_status()
            session_status = await response.json()
            if session_status["status"] == "ready":
                session_url = session_status["url"]
                break
            print(f"Session {session_id} is notready yet")
            await asyncio.sleep(2)
        else:
            raise RuntimeError("Given up waiting on session")

        async with session.ws_connect(f"{session_url}/ws/feature_selection_applet") as ws:
            asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending some feature extractors=======")
            await ws.send_json([
                {"__class__": "GaussianSmoothing", "sigma": 0.3, "axis_2d": "z"},
                {"__class__": "HessianOfGaussianEigenvalues", "scale": 0.7, "axis_2d": "z"},
            ])
            print("done sending feature extractors<<<<<")

        async with session.ws_connect(f"{session_url}/ws/brushing_applet") as ws:
            asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending some annotations=======")
            brush_strokes = [
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=140, y=150), Point5D.zero(x=145, y=155)],
                    color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=238, y=101), Point5D.zero(x=229, y=139)],
                    color=Color(r=np.uint8(0), g=np.uint8(255), b=np.uint8(0)),
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=283, y=87), Point5D.zero(x=288, y=92)],
                    color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
                    raw_data=ds
                ),
                Annotation.interpolate_from_points(
                    voxels=[Point5D.zero(x=274, y=168), Point5D.zero(x=256, y=191)],
                    color=Color(r=np.uint8(255), g=np.uint8(0), b=np.uint8(0)),
                    raw_data=ds
                ),
            ]
            await ws.send_json([
                a.to_json_data() for a in brush_strokes
            ])
            print("done sending annotations<<<<<")


            import pprint
            import requests
            from concurrent.futures import ProcessPoolExecutor
            import urllib.parse

            encoded_ds_url = urllib.parse.quote(ds.url)

            response_tasks = {}
            for tile in Interval5D.zero(x=(0, 697), y=(0, 450), c=(0, 3)).get_tiles(tile_shape=Shape5D(x=256, y=256, c=2)):
                url = f"{session_url}/predicting_applet/{encoded_ds_url}/data/{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_0-1"
                print(f"---> Requesting {url}")
                response_tasks[tile] = session.get(url)

            for tile, resp in response_tasks.items():
                async with resp as response:
                    print("Status:", response.status)
                    print("Content-type:", response.headers['content-type'])

                    tile_bytes = await response.content.read()
                    print(f"Got predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

                    raw_data = np.frombuffer(tile_bytes, dtype=np.uint8).reshape(2, tile.shape.y, tile.shape.x)
                    a = Array5D(raw_data, axiskeys="cyx")
                    a.show_channels()

            global finished;
            finished = True



asyncio.run(main())
