import aiohttp
import asyncio
import json
import numpy

from ndstructs import Array5D


async def main():
    raw_data = "http://localhost:8000/cropped1.png"
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('http://localhost:5000/wf') as ws:
            print("sending a data source=======")
            await ws.send_str(json.dumps(
                {
                    "applet_name": "data_selection_applet",
                    "method_name": "add",
                    "args": {
                        "items": [
                            {"raw_data": raw_data}
                        ]
                    }
                },
                indent=4
            ))
            print("done sending datasource<<<<<")

            print("sending some feature extractors=======")
            await ws.send_str(json.dumps(
                {
                    "applet_name": "feature_selection_applet",
                    "method_name": "add",
                    "args": {
                        "items": [
                            {"__class__": "GaussianSmoothing", "sigma": 0.3, "axis_2d": "z"},
                            {"__class__": "HessianOfGaussianEigenvalues", "scale": 0.7, "axis_2d": "z"},
                        ]
                    }
                },
                indent=4
            ))
            print("done sending feature extractors<<<<<")


            print("sending some annotations=======")
            await ws.send_str(json.dumps(
                {
                    "applet_name": "brushing_applet",
                    "method_name": "add",
                    "args": {
                        "items": [
                            {
                                "voxels": [{"x": 140, "y": 150}, {"x": 145, "y": 155}],
                                "color": {"r": 0, "g": 255, "b": 0},
                                "raw_data": raw_data
                            },
                            {
                                "voxels": [{"x": 238, "y": 101}, {"x": 229, "y": 139}],
                                "color": {"r": 0, "g": 255, "b": 0},
                                "raw_data": raw_data
                            },
                            {
                                "voxels": [{"x": 283, "y": 87}, {"x": 288, "y": 92}],
                                "color": {"r": 255, "g": 0, "b": 0},
                                "raw_data": raw_data
                            },
                            {
                                "voxels": [{"x": 274, "y": 168}, {"x": 256, "y": 191}],
                                "color": {"r": 255, "g": 0, "b": 0},
                                "raw_data": raw_data
                            },
                        ]
                    }
                },
                indent=4
            ))
            print("done sending annotations<<<<<")

            print(f"Requesting predictions========================")
            async with session.get("http://localhost:5000/predictions_export_applet/0/data/0-500_0-256_0-1") as response:
                print("Status:", response.status)
                print("Content-type:", response.headers['content-type'])

                tile_bytes = await response.content.read()
                print(f"Got predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")

                raw_data = numpy.frombuffer(tile_bytes, dtype=numpy.uint8).reshape(2, 256, 500)
                a = Array5D(raw_data, axiskeys="cyx")
                a.show_channels()
            print(f"    shown predictions<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")



            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    pass
                if msg.type == aiohttp.WSMsgType.TEXT:
                    print(f"Response from server: {msg.data}")
            #     if msg.type == aiohttp.WSMsgType.TEXT:
            #         if msg.data == 'close cmd':
            #             await ws.close()
            #             break
            #         else:
            #             await ws.send_str(msg.data + '/answer')
            #     elif msg.type == aiohttp.WSMsgType.ERROR:
            #         break

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
