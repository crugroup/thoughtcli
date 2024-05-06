import os
import yaml
from pathlib import Path

import click
from prompt_toolkit.shortcuts import (
    radiolist_dialog,
    message_dialog,
    checkboxlist_dialog,
    input_dialog,
)

from thoughtspot_rest_api_v1.tsrestapiv2 import TSRestApiV2
from thoughtspot_rest_api_v1.tsrestapiv1 import (
    TSRestApiV1,
    MetadataTypes,
    MetadataSubtypes,
)


@click.command()
def cli():
    config = read_config()

    profile = radiolist_dialog(
        title="Select Profile",
        text="Select a profile",
        values=[(key, key) for key in config["profiles"].keys()],
    ).run()

    if profile is None:
        return

    active_profile = config["profiles"][profile]

    ts_client_v1 = TSRestApiV1(
        server_url=active_profile["server_url"],
    )

    ts_client_v2 = TSRestApiV2(
        server_url=active_profile["server_url"],
    )

    while (
        main_manu := radiolist_dialog(
            title="Main Menu",
            text="Select an option",
            values=[
                ("git_commit", "Git Commit"),
                ("test", "Test connection"),
            ],
        ).run()
    ) is not None:
        result = "Unknown option"

        if main_manu == "test":
            result = test_connection(ts_client_v2, active_profile)
        elif main_manu == "git_commit":
            result = git_commit(ts_client_v1, ts_client_v2, active_profile)

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


def test_connection(ts_client_v2: TSRestApiV2, active_profile):
    try:
        ts_client_v2.auth_session_login(
            username=active_profile["username"], password=active_profile["password"]
        )
        ts_client_v2.auth_session_logout()
        return "Connection Successful"
    except Exception as e:
        return f"Connection Failed: {e}"


def git_commit(ts_client_v1: TSRestApiV1, ts_client_v2: TSRestApiV2, active_profile):
    try:
        ts_client_v1.session_login(
            username=active_profile["username"], password=active_profile["password"]
        )

        if active_profile.get("org"):
            ts_client_v1.session_orgs_put(active_profile["org"])

        tables = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.TABLE,
            subtypes=[MetadataSubtypes.TABLE, MetadataSubtypes.VIEW],
            sort="name",
        )

        def format_name(item):
            return item["name"] + " [" + item["id"] + "]"

        selected_tables = checkboxlist_dialog(
            title="Select Tables and Views",
            text="Select tables and views to commit",
            values=[(table["id"], format_name(table)) for table in tables],
        ).run()

        worksheets = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.WORKSHEET,
            subtypes=[MetadataSubtypes.WORKSHEET],
            sort="name",
        )

        selected_worksheets = checkboxlist_dialog(
            title="Select Worksheets",
            text="Select worksheets to commit",
            values=[
                (worksheet["id"], format_name(worksheet)) for worksheet in worksheets
            ],
        ).run()

        liveboards = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.LIVEBOARD, sort="name"
        )

        selected_liveboards = checkboxlist_dialog(
            title="Select Liveboards",
            text="Select liveboards to commit",
            values=[
                (liveboard["id"], format_name(liveboard)) for liveboard in liveboards
            ],
        ).run()
        ts_client_v1.session_logout()

        ts_client_v2.auth_session_login(
            username=active_profile["username"], password=active_profile["password"]
        )

        comment = input_dialog(
            title="Commit message", text="Please enter commit message:"
        ).run()

        ts_client_v2.vcs_git_branches_commit(
            request={
                "metadata": [
                    {"identifier": table_id, "type": MetadataTypes.TABLE}
                    for table_id in selected_tables
                ]
                + [
                    {"identifier": worksheet_id, "type": MetadataTypes.WORKSHEET}
                    for worksheet_id in selected_worksheets
                ]
                + [
                    {"identifier": liveboard_id, "type": MetadataTypes.LIVEBOARD}
                    for liveboard_id in selected_liveboards
                ],
                "comment": comment,
            }
        )

        ts_client_v2.auth_session_logout()

        return "Commit Successful"
    except Exception as e:
        return f"Commit Failed: {e}"
