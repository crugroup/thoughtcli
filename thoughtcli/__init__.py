import os
import yaml
import logging
from pathlib import Path
import json
import tempfile

import click
from prompt_toolkit.shortcuts import (
    radiolist_dialog,
    message_dialog,
    checkboxlist_dialog,
    input_dialog,
)

# from thoughtspot_rest_api_v1.tsrestapiv2 import TSRestApiV2
# TODO: remove once Thoughtspot fix their stuff

from thoughtcli.ts_overwrite import TSRestApiV2Org as TSRestApiV2
from thoughtspot_rest_api_v1.tsrestapiv1 import (
    TSRestApiV1,
    MetadataTypes,
    MetadataSubtypes,
)

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
                ("test", "Test connection"),
                ("git_commit", "Git commit"),
                ("git_deploy_validate", "Git deployment validate"),
                ("git_deploy", "Git deploy"),
            ],
        ).run()
    ) is not None:
        result = "Unknown option"

        if main_manu == "test":
            result = test_connection(ts_client_v2, active_profile)
        elif main_manu == "git_commit":
            result = git_commit(ts_client_v1, ts_client_v2, active_profile)
        elif main_manu == "git_deploy_validate":
            result = git_deploy_validate(ts_client_v2, active_profile)
        elif main_manu == "git_deploy":
            result = git_deploy(ts_client_v2, active_profile)

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
            username=active_profile["username"],
            password=active_profile["password"],
            org_identifier=active_profile.get("org_identifier"),
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

        if active_profile.get("org_identifier"):
            ts_client_v1.session_orgs_put(active_profile["org_identifier"])

        def format_name(item):
            return item["name"] + " [" + item["id"] + "]"

        tables = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.TABLE,
            subtypes=[MetadataSubtypes.TABLE, MetadataSubtypes.VIEW],
            sort="name",
        )

        selected_tables = (
            checkboxlist_dialog(
                title="Select Tables and Views",
                text="Select tables and views to commit",
                values=[(table["id"], format_name(table)) for table in tables],
            ).run()
            or []
        )

        worksheets = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.WORKSHEET,
            subtypes=[MetadataSubtypes.WORKSHEET],
            sort="name",
        )

        selected_worksheets = (
            checkboxlist_dialog(
                title="Select Worksheets",
                text="Select worksheets to commit",
                values=[
                    (worksheet["id"], format_name(worksheet))
                    for worksheet in worksheets
                ],
            ).run()
            or []
        )

        liveboards = ts_client_v1.metadata_listobjectheaders(
            object_type=MetadataTypes.LIVEBOARD, sort="name"
        )

        selected_liveboards = (
            checkboxlist_dialog(
                title="Select Liveboards",
                text="Select liveboards to commit",
                values=[
                    (liveboard["id"], format_name(liveboard))
                    for liveboard in liveboards
                ],
            ).run()
            or []
        )
        ts_client_v1.session_logout()

        ts_client_v2.auth_session_login(
            username=active_profile["username"],
            password=active_profile["password"],
            org_identifier=active_profile.get("org_identifier"),
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
                {"identifier": liveboard_id, "type": "LIVEBOARD"}
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

        ts_client_v2.auth_session_logout()

        return "Commit Successful"
    except Exception as e:
        return f"Commit Failed: {e}"


def git_deploy_validate(ts_client_v2: TSRestApiV2, active_profile):
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

        ts_client_v2.auth_session_login(
            username=active_profile["username"],
            password=active_profile["password"],
            org_identifier=active_profile.get("org_identifier"),
        )

        response = ts_client_v2.vcs_git_branches_validate(
            source_branch_name=source_branch, target_branch_name=target_branch
        )

        ts_client_v2.auth_session_logout()

        response_str = json.dumps(response, indent=4)
        logger.info(response_str)
        return f"Deployment validation successful: {response_str}"
    except Exception as e:
        return f"Deployment validation failed: {e}"


def git_deploy(ts_client_v2: TSRestApiV2, active_profile):
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

        ts_client_v2.auth_session_login(
            username=active_profile["username"],
            password=active_profile["password"],
            org_identifier=active_profile.get("org_identifier"),
        )

        response = ts_client_v2.vcs_git_commits_deploy(
            request={
                "branch_name": deploy_branch,
                "deploy_type": deploy_type,
                "deploy_policy": deploy_policy,
            }
        )

        ts_client_v2.auth_session_logout()

        response_str = json.dumps(response, indent=4)
        logger.info(response_str)
        return f"Deployment successful: {response_str}"
    except Exception as e:
        return f"Deployment failed: {e}"
