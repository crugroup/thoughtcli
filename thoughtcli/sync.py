"""Metadata sync handler for ThoughtSpot table descriptions."""

import json
import logging

logger = logging.getLogger("thoughtcli")

DEFAULT_SYNC_ATTRIBUTES = ["DESCRIPTION"]




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
