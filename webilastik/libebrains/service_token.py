import requests
import json

from ndstructs.utils.json_serializable import ensureJsonInt, ensureJsonObject, ensureJsonString


class ServiceToken:
    def __init__(
        self,
        access_token: str,
        expires_in: int,
        refresh_expires_in: int,
        token_type: str,
        not_before_policy: int,
        scope: str,
    ):
        self.access_token = access_token
        self.expires_in = expires_in
        self.not_before_policy = not_before_policy
        self.refresh_expires_in = refresh_expires_in
        self.scope = scope
        self.token_type = token_type
        super().__init__()

    @classmethod
    def get(cls, *, client_id: str, client_secret: str) -> "ServiceToken":
        response = requests.post(
            "https://iam.ebrains.eu/auth/realms/hbp/protocol/openid-connect/token",
            auth=('developer', ''),
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "email profile team group clb.wiki.read clb.wiki.write", #FIXME
                "grant_type": "client_credentials",
            },
        )
        print(f"Get ServiceToken response:\n:{json.dumps(response.json(), indent=4)}")
        response.raise_for_status()
        payload = ensureJsonObject(response.json())

        return ServiceToken(
            access_token=ensureJsonString(payload.get("access_token")),
            expires_in=ensureJsonInt(payload.get("expires_in")),
            not_before_policy=ensureJsonInt(payload.get("not-before-policy")),
            refresh_expires_in=ensureJsonInt(payload.get("refresh_expires_in")),
            scope=ensureJsonString(payload.get("scope")),
            token_type=ensureJsonString(payload.get("token_type")),
        )