from dataclasses import dataclass
from thoughtspot_rest_api.tsrestapiv2 import TSRestApiV2


@dataclass
class TSProfile:
    server_url: str
    username: str | None = None
    password: str | None = None
    org_identifier: int | None = None
    secret_key: str | None = None


class TSConnection:
    def __init__(self, profile: TSProfile, metadata_max_size: int = 1000):
        self.metadata_max_size = metadata_max_size
        self.v2 = V2Connection(profile)
