"""Metadata sync handler for ThoughtSpot table descriptions."""

import json
import logging

logger = logging.getLogger("thoughtcli")

DEFAULT_SYNC_ATTRIBUTES = ["DESCRIPTION"]


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


class SyncMetadata:
    """Helper class to handle table metadata resyncing"""

    def __init__(self, client):
        self.client = client

    def resync_tables(
        self, connection_id: str, table_ids: list, sync_attributes: list = None
    ) -> dict:
        """
        Resync table metadata for the defined connection.

        Makes a POST request to: /connections/{connection_id}/resync-metadata

        Args:
            connection_id: Identifier of the connection to resync.
            table_ids: List of table identifiers to resync.
            sync_attributes: List of attributes to sync, defaults to ["DESCRIPTION"].

        Returns:
            The parsed API response.
        """
        if not connection_id:
            raise ValueError("connection_id is required")

        if not table_ids:
            raise ValueError("table_ids must contain at least one table id")

        sync_attributes = sync_attributes or DEFAULT_SYNC_ATTRIBUTES

        payload = {
            "tables": table_ids,
            "sync_attributes": sync_attributes,
        }
        endpoint = f"connections/{connection_id}/resync-metadata"

        logger.info(
            f"Resyncing metadata for connection {connection_id}: {json.dumps(payload)}"
        )

        return self.client.post_request(endpoint=endpoint, request=payload)
