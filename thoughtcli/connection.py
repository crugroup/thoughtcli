from dataclasses import dataclass
from thoughtspot_rest_api_v1.tsrestapiv2 import TSRestApiV2


@dataclass
class TSProfile:
    server_url: str
    username: str | None = None
    password: str | None = None
    org_identifier: int | None = None
    api_key: str | None = None


class TSConnection:
    def __init__(self, profile: TSProfile):
        self.profile = profile
        self.user_pass_auth = profile.username and profile.password


class V2Connection(TSConnection):
    def __init__(self, profile: TSProfile):
        super().__init__(profile)
        self.client = TSRestApiV2(server_url=profile.server_url)

    def __enter__(self):
        self.client.auth_session_login(
            username=self.profile.username,
            password=self.profile.password,
            org_identifier=self.profile.org_identifier,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.user_pass_auth:
            self.client.auth_session_logout()


class TSConnection:
    def __init__(self, profile: TSProfile, metadata_max_size: int = 1000):
        self.metadata_max_size = metadata_max_size
        self.v2 = V2Connection(profile)
