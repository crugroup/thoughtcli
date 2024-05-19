# ThougthCLI

CLI for Thoughtspot. Wouldn't be needed if Thoughtspot Devs didn't take 6
months to implement a GUI for Git support. It still isn't done. This took 5 hours to build.

## Installation

```bash
pip install thoughtcli
```

## Configuration

Place a `config.yaml` file in `~/.thoughtcli/` with the following content:

```yaml
profiles:
  dev:
    server_url: https://your domain.thoughtspot.cloud
    username: user@domain.com
    password: yourpassword
    org_identifier: 123456789
```

You can also set the patho to the `config.yaml` file with `THOUGHTCLI_CONFIG_PATH` environment variable.

## Usage

```bash
thcli
```
