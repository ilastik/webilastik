import aiohttp
import asyncio
import json
from aiohttp.client_ws import ClientWebSocketResponse
from ndstructs.point5D import Interval5D, Shape5D
import numpy
import uuid
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor

from ndstructs import Array5D

finished = False

async def read_server_status(websocket: ClientWebSocketResponse):
    async for message in websocket:
        print(f"Server status update: {message.data}")
        if finished:
            break

async def main():
    raw_data = "http://localhost:8000/cropped1.png"
    async with aiohttp.ClientSession() as session:

        print(f"Creating new session--------------")
        async with session.post(f"http://localhost:5000/session", json={"session_duration": 60}) as response:
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

        async with session.ws_connect(f"{session_url}/ws/data_selection_applet") as ws:
            asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending a data source=======")
            await ws.send_json({
                "method_name": "set_state",
                "state": [
                    {"raw_data": {"url": raw_data}}
                ]
            })
            print("done sending datasource<<<<<")

        async with session.ws_connect(f"{session_url}/ws/feature_selection_applet") as ws:
            asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending some feature extractors=======")
            await ws.send_json({
                "method_name": "set_state",
                "state": [
                    {"__class__": "GaussianSmoothing", "sigma": 0.3, "axis_2d": "z"},
                    {"__class__": "HessianOfGaussianEigenvalues", "scale": 0.7, "axis_2d": "z"},
                ]
            })
            print("done sending feature extractors<<<<<")

        async with session.ws_connect(f"{session_url}/ws/brushing_applet") as ws:
            asyncio.get_event_loop().create_task(read_server_status(ws))
            print("sending some annotations=======")
            await ws.send_json({
                "method_name": "set_state",
                "state": [
                    {
                        "voxels": [{"x": 140, "y": 150}, {"x": 145, "y": 155}],
                        "color": {"r": 0, "g": 255, "b": 0},
                        "raw_data": {"url": raw_data}
                    },
                    {
                        "voxels": [{"x": 238, "y": 101}, {"x": 229, "y": 139}],
                        "color": {"r": 0, "g": 255, "b": 0},
                        "raw_data": {"url": raw_data}
                    },
                    {
                        "voxels": [{"x": 283, "y": 87}, {"x": 288, "y": 92}],
                        "color": {"r": 255, "g": 0, "b": 0},
                        "raw_data": {"url": raw_data}
                    },
                    {
                        "voxels": [{"x": 274, "y": 168}, {"x": 256, "y": 191}],
                        "color": {"r": 255, "g": 0, "b": 0},
                        "raw_data": {"url": raw_data}
                    },
                ]
            })
            print("done sending annotations<<<<<")


            import pprint
            import requests
            from concurrent.futures import ProcessPoolExecutor
            print(f"Requesting predictions========================")
            with ProcessPoolExecutor(max_workers=8) as executor:
                future_generator = executor.map(
                    requests.get,
                    [
                        f"{session_url}/predictions_export_applet/{uuid.uuid4()}/0/data/{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_0-1"
                        for tile in
                        Interval5D.zero(x=(0, 697), y=(0, 450), c=(0, 3)).get_tiles(tile_shape=Shape5D(x=256, y=256, c=2))
                    ]
                )
                for f in list(future_generator):
                    print(f"Response : {f.status_code}")

            response_tasks = {}
            for tile in Interval5D.zero(x=(0, 697), y=(0, 450), c=(0, 3)).get_tiles(tile_shape=Shape5D(x=256, y=256, c=2)):
                response_tasks[tile] = session.get(
                    f"{session_url}/predictions_export_applet/{uuid.uuid4()}/0/data/{tile.x[0]}-{tile.x[1]}_{tile.y[0]}-{tile.y[1]}_0-1"
                )

            for tile, resp in response_tasks.items():
                async with resp as response:
                    print("Status:", response.status)
                    print("Content-type:", response.headers['content-type'])

                    tile_bytes = await response.content.read()
                    print(f"Got predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

                    raw_data = numpy.frombuffer(tile_bytes, dtype=numpy.uint8).reshape(2, tile.shape.y, tile.shape.x)
                    a = Array5D(raw_data, axiskeys="cyx")
                    a.show_channels()

            global finished;
            finished = True



asyncio.run(main())
