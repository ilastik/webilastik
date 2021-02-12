import multiprocessing
from typing import Any, Dict
from multiprocessing import Process

import aiohttp


from aiohttp import web

from webilastik.ui.workflow.ws_pixel_classification_workflow import WsPixelClassificationWorkflow

def start_pixel_classification_session(port: int):
    workflow = WsPixelClassificationWorkflow()
    workflow.run(port=port)

class LocalSessionAllocator:
    def __init__(self, session_port_range: range):
        self.available_ports = {i for i in session_port_range}
        self.sessions : Dict[int, Process] = {}

        self.app = web.Application()
        self.app.add_routes([
            web.post('/session', self.spawn_session), #type: ignore
        ])

    def spawn_session(self, request: web.Request):
        port = self.available_ports.pop() #FIXME: put this back in the pool somehow
        session = Process(target=start_pixel_classification_session, args=(port,))
        self.sessions[port] = session
        session.start()

        return web.Response(
            text=f"http://localhost:{port}",
            headers={"Access-Control-Allow-Origin": "*"})


    def run(self, port: int):
        if port in self.available_ports:
            raise ValueError(f"Port {port} is allocated as a session port!")
        web.run_app(self.app, port=port)

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn') #start a fresh interpreter so it doesn't 'inherit' the event loop
    LocalSessionAllocator(session_port_range=range(5001, 5050)).run(port=5000)
