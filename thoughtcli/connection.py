from dataclasses import dataclass
from thoughtspot_rest_api.tsrestapiv2 import TSRestApiV2
import json
import logging

logger = logging.getLogger("thoughtcli")


@dataclass
class TSProfile:
    server_url: str
    username: str | None = None
    password: str | None = None
    org_identifier: int | None = None
    secret_key: str | None = None


class Auth:
    def __init__(self, profile: TSProfile):
        self.profile = profile
        self.user_pass_auth = profile.username and profile.password


class V2Connection(Auth):
    def __init__(self, profile: TSProfile):
        super().__init__(profile)
        self.client = TSRestApiV2(server_url=profile.server_url)

    def __enter__(self):
        if self.user_pass_auth:
            self.client.auth_session_login(
                username=self.profile.username,
                password=self.profile.password,
                org_identifier=self.profile.org_identifier,
            )
        else:
            resp = self.client.auth_token_full(
                username=self.profile.username,
                secret_key=self.profile.secret_key,
                org_id=self.profile.org_identifier,
            )
            self.client.bearer_token = resp["token"]

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.auth_session_logout()


class TSConnection:
    def __init__(self, profile: TSProfile, metadata_max_size: int = 1000):
        self.metadata_max_size = metadata_max_size
        self.v2 = V2Connection(profile)


def fetch_connection_options(client, record_size: int) -> list:
    """Fetch available connections as (id, name) options for a selection dialog"""
    try:
        connections_response = client.connection_search(
            request={"record_size": record_size}
        )
    except Exception:
        # connection_search may not be available on every deployment
        connections_response = []

    return [(conn["id"], conn["name"]) for conn in connections_response]


def fetch_connection_tables(client, connection_id: str, record_size: int) -> list:
    """Fetch (id, name) options for the tables belonging to a single connection.

    Uses connection_search scoped to connection_id so that "all tables" only
    considers tables within that connection, not every connection.
    """
    request = {
        "connection_identifiers": [connection_id],
        "record_size": record_size,
        "include_details": True,
    }
    try:
        connections_response = client.connection_search(request=request)
    except Exception:
        logger.exception(f"connection_search failed for request: {json.dumps(request)}")
        connections_response = []

    logger.debug(
        f"connection_search response for connection {connection_id}: "
        f"{json.dumps(connections_response, default=str)}"
    )

    if not connections_response:
        return []

    connection = next(
        (conn for conn in connections_response if conn.get("id") == connection_id),
        None,
    )
    if connection is None:
        logger.warning(
            f"connection_search did not return connection {connection_id}; "
            f"got ids: {[conn.get('id') for conn in connections_response]}"
        )
        return []

    connection_tables = (connection.get("details") or {}).get("tables") or []

    tables = []
    for item in connection_tables:
        table_id = item.get("id")
        table_name = item.get("name")
        if table_id and table_name:
            tables.append((table_id, table_name))

    tables.sort(key=lambda table: table[1].lower())

    logger.debug(f"Parsed table options for connection {connection_id}: {tables}")

    return tables