import json
import logging
import os
import tempfile
from pathlib import Path

import click
import yaml
from requests.exceptions import HTTPError
from textual import work
from textual.app import App

from thoughtspot_rest_api.tsrestapiv1 import (
    MetadataTypes,
    MetadataSubtypes,
)
from thoughtspot_rest_api.tsrestapiv2 import TSTypesV2

from thoughtcli.connection import TSProfile, TSConnection
from thoughtcli.sync import SyncMetadata, fetch_connection_options, fetch_connection_tables
from thoughtcli.ui import (
    RadioListDialog,
    CheckboxListDialog,
    ConfirmDialog,
    InputDialog,
    MessageDialog,
)

logger = logging.getLogger("thoughtcli")
logger.setLevel(logging.DEBUG)
logfile = tempfile.NamedTemporaryFile(delete=False, prefix="thoughtcli-", suffix=".log")
handler = logging.FileHandler(logfile.name)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


class ThoughtCLIApp(App[None]):
    """Main Textual application for ThoughtCLI."""

    THEME = "textual-light"
    CSS = """
    Button {
        border: round $primary;
    }
    """

    def __init__(self, config: dict):
        super().__init__()
        self._config = config

    def on_mount(self) -> None:
        self._run_main_flow()

    @work
    async def _run_main_flow(self) -> None:
        profile = await self.push_screen_wait(
            RadioListDialog(
                title="Select Profile",
                text="Select a profile",
                values=[(key, key) for key in self._config["profiles"].keys()],
            )
        )

        if profile is None:
            self.exit()
            return

        ts_connection = TSConnection(TSProfile(**self._config["profiles"][profile]))

        while True:
            action = await self.push_screen_wait(
                RadioListDialog(
                    title="Main Menu",
                    text="Select an option",
                    values=[
                        ("test", "Test connection"),
                        ("sync_tables", "Sync tables descriptions"),
                        ("git_commit", "Git commit"),
                        ("git_deploy_validate", "Git deployment validate"),
                        ("git_deploy", "Git deploy"),
                    ],
                )
            )

            if action is None:
                break

            result = "Unknown option"
            if action == "test":
                result = self._test_connection(ts_connection)
            elif action == "sync_tables":
                result = await self._sync_tables(ts_connection)
            elif action == "git_commit":
                result = await self._git_commit(ts_connection)
            elif action == "git_deploy_validate":
                result = await self._git_deploy_validate(ts_connection)
            elif action == "git_deploy":
                result = await self._git_deploy(ts_connection)

            await self.push_screen_wait(MessageDialog(text=result))

        self.exit()

    async def _git_commit(self, ts_connection: TSConnection) -> str:
        def format_name_v2(item):
            return item["metadata_id"], item["metadata_name"] + " [" + item[
                "metadata_id"
            ] + "]"

        try:
            with ts_connection.v2 as ts_client_v2:
                tables = ts_client_v2.client.metadata_search(
                    {
                        "metadata": [{"type": MetadataTypes.TABLE}],
                        "record_size": ts_connection.metadata_max_size,
                        "sort_options": {"field_name": "NAME"},
                    }
                )

                selected_tables = await self.push_screen_wait(
                    CheckboxListDialog(
                        title="Select Tables and Views",
                        text="Select tables and views to commit",
                        values=[
                            format_name_v2(table)
                            for table in tables
                            if table["metadata_header"]["type"]
                            == MetadataSubtypes.TABLE
                        ],
                    )
                )

                selected_worksheets = await self.push_screen_wait(
                    CheckboxListDialog(
                        title="Select Worksheets",
                        text="Select worksheets to commit",
                        values=[
                            format_name_v2(table)
                            for table in tables
                            if table["metadata_header"]["type"]
                            == MetadataSubtypes.WORKSHEET
                            or table["metadata_header"]["type"] == "TABLE"
                        ],
                    )
                )

                liveboards = ts_client_v2.client.metadata_search(
                    {
                        "metadata": [{"type": TSTypesV2.LIVEBOARD}],
                        "record_size": ts_connection.metadata_max_size,
                        "sort_options": {"field_name": "NAME"},
                    }
                )

                selected_liveboards = await self.push_screen_wait(
                    CheckboxListDialog(
                        title="Select Liveboards",
                        text="Select liveboards to commit",
                        values=[format_name_v2(liveboard) for liveboard in liveboards],
                    )
                )

                comment = await self.push_screen_wait(
                    InputDialog(
                        title="Commit message", text="Please enter commit message:"
                    )
                )

                if not comment:
                    return "Cancelled"

                selected_metadata = (
                    [
                        {"identifier": table_id, "type": MetadataTypes.TABLE}
                        for table_id in selected_tables
                    ]
                    + [
                        {"identifier": ws_id, "type": MetadataTypes.WORKSHEET}
                        for ws_id in selected_worksheets
                    ]
                    + [
                        {"identifier": lb_id, "type": TSTypesV2.LIVEBOARD}
                        for lb_id in selected_liveboards
                    ]
                )

                if not selected_metadata:
                    return "No metadata selected"

                ts_client_v2.client.vcs_git_branches_commit(
                    request={"metadata": selected_metadata, "comment": comment}
                )

            return "Commit Successful"
        except HTTPError as e:
            return f"Commit Failed: {e}\n{e.response.text}"

    async def _git_deploy_validate(self, ts_connection: TSConnection) -> str:
        try:
            source_branch = await self.push_screen_wait(
                InputDialog(
                    title="Source branch", text="Please input the source branch:"
                )
            )
            if not source_branch:
                return "Cancelled"

            target_branch = await self.push_screen_wait(
                InputDialog(
                    title="Target branch", text="Please input the target branch:"
                )
            )
            if not target_branch:
                return "Cancelled"

            with ts_connection.v2 as ts_client_v2:
                response = ts_client_v2.client.vcs_git_branches_validate(
                    source_branch_name=source_branch, target_branch_name=target_branch
                )

            response_str = json.dumps(response, indent=4)
            logger.info(response_str)
            return f"Deployment validation successful: {response_str}"
        except HTTPError as e:
            return f"Deployment validation failed: {e}\n{e.response.text}"

    async def _git_deploy(self, ts_connection: TSConnection) -> str:
        try:
            deploy_branch = await self.push_screen_wait(
                InputDialog(
                    title="Deploy branch", text="Please input the deploy branch:"
                )
            )
            if not deploy_branch:
                return "Cancelled"

            deploy_type = await self.push_screen_wait(
                RadioListDialog(
                    title="Deploy type",
                    text="Select deploy type",
                    values=[("DELTA", "Delta"), ("FULL", "Full")],
                )
            )
            if not deploy_type:
                return "Cancelled"

            deploy_policy = await self.push_screen_wait(
                RadioListDialog(
                    title="Deploy policy",
                    text="Select deploy policy",
                    values=[
                        ("VALIDATE_ONLY", "Validate only"),
                        ("ALL_OR_NONE", "All or none"),
                        ("PARTIAL", "Partial"),
                    ],
                )
            )
            if not deploy_policy:
                return "Cancelled"

            with ts_connection.v2 as ts_client_v2:
                response = ts_client_v2.client.vcs_git_commits_deploy(
                    request={
                        "branch_name": deploy_branch,
                        "deploy_type": deploy_type,
                        "deploy_policy": deploy_policy,
                    }
                )

            response_str = json.dumps(response, indent=4)
            logger.info(response_str)
            return f"Deployment successful: {response_str}"
        except HTTPError as e:
            return f"Deployment failed: {e}\n{e.response.text}"

    def _test_connection(self, ts_connection: TSConnection) -> str:
        try:
            with ts_connection.v2:
                return "Connection Successful"
        except Exception as e:
            return f"Connection Failed: {e}"

    async def _sync_tables(self, ts_connection: TSConnection) -> str:
        """
        Sync table descriptions from the connection.

        Allows users to:
        1. Select a connection to resync tables from
        2. Choose which tables to resync (or resync all)
        """
        try:
            with ts_connection.v2 as ts_client_v2:
                # Fetch available connections
                connection_options = fetch_connection_options(
                    ts_client_v2.client, ts_connection.metadata_max_size
                )

                if not connection_options:
                    return "No connections available to sync"

                # User selects connection
                selected_connection_id = await self.push_screen_wait(
                    RadioListDialog(
                        title="Select Connection",
                        text="Select a connection to resync tables from",
                        values=connection_options,
                    )
                )

                if selected_connection_id is None:
                    return "Cancelled"

                # Ask about sync scope
                sync_scope = await self.push_screen_wait(
                    RadioListDialog(
                        title="Choose Tables to Sync",
                        text="Would you like to sync specific tables, or every table in this connection?",
                        values=[
                            ("selected_tables", "Choose specific tables"),
                            ("all_tables", "Sync all tables"),
                        ],
                    )
                )

                if sync_scope is None:
                    return "Cancelled"

                # Fetch tables available for selection, scoped to the selected connection
                table_options = fetch_connection_tables(
                    ts_client_v2.client,
                    selected_connection_id,
                    ts_connection.metadata_max_size,
                )

                if not table_options:
                    return "No tables available to sync for this connection"

                if sync_scope == "all_tables":
                    selected_table_ids = [table_id for table_id, _ in table_options]
                else:
                    selected_table_ids = await self.push_screen_wait(
                        CheckboxListDialog(
                            title="Select Tables",
                            text="Select tables to sync",
                            values=table_options,
                        )
                    )

                    if not selected_table_ids:
                        return "Cancelled"

                # Confirm the selected tables before syncing
                table_names = dict(table_options)
                confirmation_text = "\n".join(
                    f"- {table_names.get(table_id, table_id)}"
                    for table_id in selected_table_ids
                )
                confirmed = await self.push_screen_wait(
                    ConfirmDialog(
                        title="Confirm Sync",
                        text=f"Sync the following tables?\n\n{confirmation_text}",
                    )
                )

                if not confirmed:
                    return "Cancelled"

                # Use SyncMetadata helper to perform the resync
                sync_handler = SyncMetadata(ts_client_v2.client)
                response = sync_handler.resync_tables(
                    connection_id=selected_connection_id,
                    table_ids=selected_table_ids,
                )

                response_str = json.dumps(response, indent=4)
                logger.info(f"Sync response: {response_str}")

                return f"✓ Sync successful!\n\n{response_str}"

        except HTTPError as e:
            error_msg = f"Sync failed: {e}\n{e.response.text}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Sync error: {str(e)}"
            logger.error(error_msg)
            return error_msg


@click.command()
def cli():
    click.echo("Writing log to: " + logfile.name)
    config = read_config()
    ThoughtCLIApp(config=config).run()


def read_config():
    config_path = os.getenv(
        "THOUGHTCLI_CONFIG_PATH", str(Path.home() / ".thoughtcli/config.yaml")
    )

    if not Path(config_path).exists():
        click.echo(f"Config file not found at {config_path}")
        click.echo(
            "Set the variable THOUGHTCLI_CONFIG_PATH to the path of the config file"
            + " or create a config file at the default path ~/.thoughtcli/config.yaml"
        )
        exit(1)

    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    return config
