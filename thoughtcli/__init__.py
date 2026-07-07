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
from thoughtcli.ui import (
    RadioListDialog,
    CheckboxListDialog,
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
                        ("ALL_OR_NONE", "All or none"),
                        ("VALIDATE_ONLY", "Validate only"),
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
