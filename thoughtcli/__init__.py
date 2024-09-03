import json
import logging
import os
import tempfile
from pathlib import Path

import click
import yaml
from prompt_toolkit.shortcuts import (
    radiolist_dialog,
    message_dialog,
    checkboxlist_dialog,
    input_dialog,
)
from requests.exceptions import HTTPError

from thoughtspot_rest_api_v1.tsrestapiv1 import (
    MetadataTypes,
    MetadataSubtypes,
)
from thoughtspot_rest_api_v1.tsrestapiv2 import TSTypesV2

from thoughtcli.connection import TSProfile, TSConnection

logger = logging.getLogger("thoughtcli")
logger.setLevel(logging.DEBUG)
logfile = tempfile.NamedTemporaryFile(delete=False, prefix="thoughtcli-", suffix=".log")
handler = logging.FileHandler(logfile.name)
handler.setLevel(logging.DEBUG)
logger.addHandler(handler)


@click.command()
def cli():
    click.echo("Writing log to: " + logfile.name)

    config = read_config()

    profile = radiolist_dialog(
        title="Select Profile",
        text="Select a profile",
        values=[(key, key) for key in config["profiles"].keys()],
    ).run()

    if profile is None:
        return

    active_profile = config["profiles"][profile]

    ts_connection = TSConnection(TSProfile(**active_profile))

    while (
        main_manu := radiolist_dialog(
            title="Main Menu",
            text="Select an option",
            values=[
                ("test", "Test connection"),
                ("git_commit", "Git commit"),
                ("git_deploy_validate", "Git deployment validate"),
                ("git_deploy", "Git deploy"),
            ],
        ).run()
    ) is not None:
        result = "Unknown option"

        if main_manu == "test":
            result = test_connection(ts_connection)
        elif main_manu == "git_commit":
            result = git_commit(ts_connection)
        elif main_manu == "git_deploy_validate":
            result = git_deploy_validate(ts_connection)
        elif main_manu == "git_deploy":
            result = git_deploy(ts_connection)

        message_dialog(text=result).run()


def read_config():
    # Check if the environment variable is set
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

    # Read the yaml config file
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)

    return config


def test_connection(ts_connection: TSConnection):
    try:
        with ts_connection.v2:
            return "Connection Successful"
    except Exception as e:
        return f"Connection Failed: {e}"


def git_commit(ts_connection: TSConnection):
    def format_name(item):
        return item["name"] + " [" + item["id"] + "]"

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

            selected_tables = (
                checkboxlist_dialog(
                    title="Select Tables and Views",
                    text="Select tables and views to commit",
                    values=[
                        format_name_v2(table)
                        for table in tables
                        if table["metadata_header"]["type"] == MetadataSubtypes.TABLE
                    ],
                ).run()
                or []
            )

            selected_worksheets = (
                checkboxlist_dialog(
                    title="Select Worksheets",
                    text="Select worksheets to commit",
                    values=[
                        format_name_v2(table)
                        for table in tables
                        if table["metadata_header"]["type"]
                        == MetadataSubtypes.WORKSHEET
                    ],
                ).run()
                or []
            )

            liveboards = ts_client_v2.client.metadata_search(
                {
                    "metadata": [{"type": TSTypesV2.LIVEBOARD}],
                    "record_size": ts_connection.metadata_max_size,
                    "sort_options": {"field_name": "NAME"},
                }
            )

            selected_liveboards = (
                checkboxlist_dialog(
                    title="Select Liveboards",
                    text="Select liveboards to commit",
                    values=[format_name_v2(liveboard) for liveboard in liveboards],
                ).run()
                or []
            )

            comment = input_dialog(
                title="Commit message", text="Please enter commit message:"
            ).run()

            if not comment:
                return "Cancelled"

            selected_metadata = (
                [
                    {"identifier": table_id, "type": MetadataTypes.TABLE}
                    for table_id in selected_tables
                ]
                + [
                    {"identifier": worksheet_id, "type": MetadataTypes.WORKSHEET}
                    for worksheet_id in selected_worksheets
                ]
                + [
                    {"identifier": liveboard_id, "type": TSTypesV2.LIVEBOARD}
                    for liveboard_id in selected_liveboards
                ]
            )

            if not selected_metadata:
                return "No metadata selected"

            ts_client_v2.vcs_git_branches_commit(
                request={
                    "metadata": selected_metadata,
                    "comment": comment,
                }
            )

        return "Commit Successful"
    except HTTPError as e:
        return f"Commit Failed: {e}\n{e.response.text}"


def git_deploy_validate(ts_connection: TSConnection):
    try:
        source_branch = input_dialog(
            title="Source branch", text="Please input the source branch:"
        ).run()

        if not source_branch:
            return "Cancelled"

        target_branch = input_dialog(
            title="Target branch", text="Please input the target branch:"
        ).run()

        if not target_branch:
            return "Cancelled"

        with ts_connection.v2 as ts_client_v2:
            response = ts_client_v2.vcs_git_branches_validate(
                source_branch_name=source_branch, target_branch_name=target_branch
            )

        response_str = json.dumps(response, indent=4)
        logger.info(response_str)
        return f"Deployment validation successful: {response_str}"
    except HTTPError as e:
        return f"Deployment validation failed: {e}\n{e.response.text}"


def git_deploy(ts_connection: TSConnection):
    try:
        deploy_branch = input_dialog(
            title="Deploy branch", text="Please input the deploy branch:"
        ).run()

        if not deploy_branch:
            return "Cancelled"

        deploy_type = radiolist_dialog(
            title="Deploy type",
            text="Select deploy type",
            values=[
                ("DELTA", "Delta"),
                ("FULL", "Full"),
            ],
        ).run()

        if not deploy_type:
            return "Cancelled"

        deploy_policy = radiolist_dialog(
            title="Deploy policy",
            text="Select deploy policy",
            values=[
                ("ALL_OR_NONE", "All or none"),
                ("VALIDATE_ONLY", "Validate only"),
            ],
        ).run()

        if not deploy_policy:
            return "Cancelled"

        with ts_connection.v2 as ts_client_v2:
            response = ts_client_v2.vcs_git_commits_deploy(
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
