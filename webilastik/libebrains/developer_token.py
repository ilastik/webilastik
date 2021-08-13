import requests
import json

from ndstructs.utils.json_serializable import ensureJsonInt, ensureJsonObject, ensureJsonString


class DeveloperToken:
    def __init__(
        self,
        access_token: str,
        expires_in: int,
        not_before_policy: int,
        refresh_expires_in: int,
        refresh_token: str,
        scope: str,
        token_type: str,
    ):
        self.access_token = access_token
        self.expires_in = expires_in
        self.not_before_policy = not_before_policy
        self.refresh_expires_in = refresh_expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.token_type = token_type

    @classmethod
    def get(cls, username: str, password: str) -> "DeveloperToken":
        response = requests.post(
            "https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            auth=('developer', ''),
            data={
                "username": username,
                "password": password,
                "grant_type": "password",
            },
        )
        print(f"Get DevToken response:\n:{json.dumps(response.json(), indent=4)}")
        response.raise_for_status()
        payload = ensureJsonObject(response.json())

        return DeveloperToken(
            access_token=ensureJsonString(payload.get("access_token")),
            expires_in=ensureJsonInt(payload.get("expires_in")),
            not_before_policy=ensureJsonInt(payload.get("not-before-policy")),
            refresh_expires_in=ensureJsonInt(payload.get("refresh_expires_in")),
            refresh_token=ensureJsonString(payload.get("refresh_token")),
            scope=ensureJsonString(payload.get("scope")),
            token_type=ensureJsonString(payload.get("token_type")),
        )
