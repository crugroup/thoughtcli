# ThoughtCLI

CLI for Thoughtspot. Wouldn't be needed if Thoughtspot Devs didn't take 6
months to implement a GUI for Git support. It still isn't done. This took 5 hours to build.

## Installation

```bash
pip install thoughtcli
```

## Configuration

Place a `config.yaml` file in `~/.thoughtcli/` with the following content:

```yaml
allow_commit: false
deploy_branches: []

profiles:
  dev:
    server_url: https://your domain.thoughtspot.cloud
    username: user@domain.com
    password: yourpassword
    org_identifier: 123456789
    allow_commit: true
    deploy_branches:
      - name_of_branch
```

If you are using a secret key the configuration file should look like this:

```yaml
allow_commit: false
deploy_branches: []

profiles:
  dev:
    server_url: https://your domain.thoughtspot.cloud
    username: user@domain.com
    secret_key: aasdf1234
    org_identifier: 123456789
    allow_commit: true
    deploy_branches:
      - name_of_branch
```

`allow_commit` enables the `git commit` option
`deploy_branches` enables the deployment option and lists the available branches to deploy defined in the file.

You can also set the patho to the `config.yaml` file with `THOUGHTCLI_CONFIG_PATH` environment variable.

## Usage

```bash
thcli
```
