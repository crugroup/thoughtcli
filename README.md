# ThoughtCLI

CLI for ThoughtSpot. Use it to:

- commit content to Git
- deploy content from Git
- sync table descriptions from your data connections

## Installation

```bash
pip install thoughtcli
```

## Configuration

Place a `config.yaml` file in `~/.thoughtcli/` with the following content:

```yaml
allow_commit: false
allow_sync: false
deploy_branches: []

profiles:
  dev:
    server_url: https://your-domain.thoughtspot.cloud
    username: user@domain.com
    password: your_password
    org_identifier: 123456789
    allow_commit: true
    allow_sync: true
    deploy_branches:
      - name_of_branch
```

If you are using a secret key, the configuration file should look like this:

```yaml
allow_commit: false
allow_sync: false
deploy_branches: []

profiles:
  dev:
    server_url: https://your-domain.thoughtspot.cloud
    username: user@domain.com
    secret_key: your_secret_key
    org_identifier: 123456789
    allow_commit: true
    allow_sync: true
    deploy_branches:
      - name_of_branch
```

- `allow_commit` enables the `Git commit` option
- `allow_sync` enables the `Sync table descriptions` option
- `deploy_branches` lists the branches you can pick as the target in `Git deployment validate` and as the branch in `Git deploy`, and enables both options

Put these settings at the top level or inside a profile.
A top-level setting applies to every profile.
A profile setting overrides the top-level one.
If a setting is missing, its menu options are hidden by default.

You can also set the path to the `config.yaml` file with the `THOUGHTCLI_CONFIG_PATH` environment variable.

## Usage

```bash
thcli
```
