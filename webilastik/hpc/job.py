from types import ClassMethodDescriptorType
import pyunicore.client as unicore_client
import json
import time
import os
from typing import Dict, List, Optional, Any
import jwt
import requests
from urllib.parse import urljoin
from collections.abc import Mapping, Iterable
from pathlib import Path


def dict_to_json_data(dic: Dict[str, Any], strip_nones=True):
    return {k:to_json_data(v, strip_nones=strip_nones) for k, v in dic.items() if v is not None}

def to_json_data(value, strip_nones=True):
    if isinstance(value, (str, int, float, type(None))):
        return value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_json_data"):
        return value.to_json_data()
    if hasattr(value, "__dict__"):
        return dict_to_json_data(value.__dict__, strip_nones=strip_nones)
    if isinstance(value, Mapping):
        return dict_to_json_data(value, strip_nones=strip_nones)
    if isinstance(value, Iterable):
        return [to_json_data(v, strip_nones=strip_nones) for v in value]
    raise ValueError(f"Don't know how to convert {value} to json data")


_FIVE_MINUTES = 5 * 60


class JobResources:
    def __init__(
        self,
        *,
        Memory: Optional[str] = None,
        Runtime: int = _FIVE_MINUTES,
        CPUs: Optional[int] = None,
        Nodes: Optional[int] = None,
        CPUsPerNode: Optional[int] = None,
        Reservation: Optional[str] = None,
    ):
        self.Memory = Memory
        self.Runtime = Runtime
        self.CPUs = CPUs
        self.Nodes = Nodes
        self.CPUsPerNode = CPUsPerNode
        self.Reservation = Reservation


class JobImport:
    def __init__(self, *, From: str, To: str):
        self.From = From
        self.To = To


class JobDescription:
    def __init__(
        self,
        *,
        Executable: str,
        Arguments: Optional[List[str]] = None,
        Environment: Dict[str, str] = None,
        Exports: Optional[List[str]] = None,
        Resources: Optional[JobResources] = None,
        Imports: Optional[List[JobImport]] = None,
        Tags: Optional[List[str]] = None,
        Project: Optional[str] = None,
    ):
        self.Executable = Executable
        self.Arguments = Arguments
        self.Environment = Environment
        self.Exports = Exports
        self.Resources = Resources
        self.Imports = Imports
        self.Tags = Tags
        self.Project = Project


class HbpClient:
    _site = None

    def __init__(
        self,
        *,
        hbp_refresh_token: str,
        hbp_app_id: str,
        hbp_app_secret: str,
        access_token: Optional[str] = None,
    ):
        self.hbp_refresh_token = hbp_refresh_token
        self.hbp_app_id = hbp_app_id
        self.hbp_app_secret = hbp_app_secret
        self.access_token = access_token

    @staticmethod
    def from_environ(access_token: Optional[str] = None) -> "HbpClient":
        return HbpClient(
            access_token=access_token,
            hbp_refresh_token=os.environ["HBP_REFRESH_TOKEN"],
            hbp_app_id=os.environ["HBP_APP_ID"],
            hbp_app_secret=os.environ["HBP_APP_SECRET"],
        )

    def token_is_valid(self):
        if self.access_token is None:
            return False
        token = json.loads(jwt.utils.base64url_decode(self.access_token.split(".")[1]).decode("ascii"))
        if token["exp"] < time.time() - (15 * 60):
            return False
        return True

    def get_token(self):
        if not self.token_is_valid():
            resp = requests.post(
                "https://services.humanbrainproject.eu/oidc/token",
                data={
                    "refresh_token": self.hbp_refresh_token,
                    "client_id": self.hbp_app_id,
                    "client_secret": self.hbp_app_secret,
                    "grant_type": "refresh_token",
                },
            )
            self.access_token = resp.json()["access_token"]
        return self.access_token

    def get_jobs(self):
        site = self._get_site()
        return site.transport.get(url=site.site_urls["jobs"])

    def get_job(self, job_id: str) -> unicore_client.Job:
        site = self._get_site()
        jobs_url = site.site_urls["jobs"]
        return unicore_client.Job(site.transport, job_url=urljoin(f"{jobs_url}/", job_id))

    def _get_site(self) -> unicore_client.Client:
        if self._site is None:
            tr = unicore_client.Transport(self.get_token())
            registry = unicore_client.Registry(tr, unicore_client._HBP_REGISTRY_URL)
            self._site = registry.site("DAINT-CSCS")
        return self._site

    def run_job(self, job_description: JobDescription) -> unicore_client.Job:
        site = self._get_site()
        return site.new_job(job_description=to_json_data(job_description))#, inputs=self.inputs)
