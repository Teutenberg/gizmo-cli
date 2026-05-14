from pathlib import Path
import click
import yaml
from .config import config_init, config_get, config_set, config_unset, config_list
from .secret import encrypt, keyring_set, keyring_get, keyring_delete, keyring_list, keyring_rotate_key, key_rotated_at
from .forge import avro_file_to_sql, DEFAULT_MODEL
from . import ollama as _ollama


INIT_PATH = Path.cwd()
TEMPLATE_PATH = Path(__file__).parent / "templates"


@click.group()
def cli():
    """Gizmo CLI."""


@cli.command()
@click.option("--database", prompt=True, help="Database name")
@click.option("--schema", prompt=True, help="Schema name")
def init_cmd(database, schema):
    """Initialize Gizmo in the current directory."""
    context = {"database": database, "schema": schema}
    config_init(TEMPLATE_PATH, context)
    keyring_rotate_key()
    click.echo(f"Gizmo initialized in '{INIT_PATH}'")


@cli.group()
def secret():
    """Manage gizmo secrets stored in the system keyring."""


@secret.command("list")
def secret_list_cmd():
    """List all secret keys stored in the keyring."""
    for key in keyring_list():
        click.echo(key)
    rotated = key_rotated_at()
    click.echo(f"\nKey last rotated: {rotated.strftime('%Y-%m-%d %H:%M:%S UTC') if rotated else 'unknown'}")


@secret.command("set")
@click.option("--name", prompt=True, help="Secret name")
@click.option("--value", prompt=True, hide_input=True, help="Secret value")
def secret_set_cmd(name: str, value: str):
    """Save a secret into the keyring."""
    keyring_set(name, value)


@secret.command("delete")
@click.argument("name")
def secret_delete_cmd(name: str):
    """Delete a secret from the keyring."""
    keyring_delete(name)


@secret.command("rotate_key")
def secret_rotate_key_cmd():
    """Rotate the encryption key and re-encrypt all stored secrets."""
    keyring_rotate_key()


@cli.group()
def config():
    """Manage the Gizmo config file."""


@config.command("list")
@click.argument("key", required=False)
def config_list_cmd(key):
    """List all config values, or a single value if KEY is given (dot notation supported)."""
    data = config_list()
    if key:
        value = config_get(key)
        if value is None:
            raise click.ClickException(f"Key '{key}' not found")
        click.echo(yaml.dump({key: value}, default_flow_style=False).strip())
    else:
        click.echo(yaml.dump(data, default_flow_style=False).strip())


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set_cmd(key, value):
    """Set a config value. Keys prefixed with 'secret_' are encrypted."""
    try:
        config_set(TEMPLATE_PATH, key, value)
    except KeyError:
        raise click.ClickException(f"Key '{key}' not found in config")


@config.command("unset")
@click.argument("key")
def config_unset_cmd(key):
    """Remove a key from the config."""
    config_unset(key)


@cli.group("ollama")
def ollama_group():
    """Manage the local Ollama installation."""


@ollama_group.command("install")
@click.option("--system", "use_system", is_flag=True, default=False,
              help="Use the official install script (requires sudo).")
def ollama_install_cmd(use_system):
    """Install Ollama. Defaults to a user-local binary install (no sudo required)."""
    click.echo("Installing Ollama...")
    try:
        binary = _ollama.install(user=not use_system)
    except RuntimeError as exc:
        raise click.ClickException(str(exc))

    if binary:
        click.echo(f"Ollama installed to {binary}")
        import os
        install_dir = str(binary.parent)
        if install_dir not in os.environ.get("PATH", "").split(":"):
            click.echo(f"  Add to your shell profile: export PATH=\"{install_dir}:$PATH\"")
        click.echo("Start the server with: ollama serve")
    else:
        click.echo("Ollama installed successfully.")


@ollama_group.command("run")
@click.option("--wait", is_flag=True, default=False, help="Wait until the service is reachable before returning.")
def ollama_run_cmd(wait):
    """Start the Ollama server in the background."""
    if _ollama.is_running():
        click.echo("Ollama is already running.")
        return
    proc = _ollama.run()
    click.echo(f"Ollama server started (pid {proc.pid}).")
    if wait:
        import time
        for _ in range(30):
            if _ollama.is_running():
                click.echo("Ollama is ready.")
                return
            time.sleep(1)
        click.echo("Timed out waiting for Ollama to become ready.", err=True)


@ollama_group.command("pull")
@click.argument("model", required=False)
def ollama_pull_cmd(model):
    """Pull a model (defaults to the model set in config)."""
    target = model or _ollama.ollama_model()
    click.echo(f"Pulling model '{target}'...")
    try:
        _ollama.pull(target)
        click.echo(f"Model '{target}' ready.")
    except RuntimeError as exc:
        raise click.ClickException(str(exc))


@ollama_group.command("status")
def ollama_status_cmd():
    """Show Ollama host, configured model, and running state."""
    import yaml as _yaml
    info = _ollama.status()
    click.echo(_yaml.dump(info, default_flow_style=False).strip())


@ollama_group.command("prompt")
@click.argument("text")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Ollama model to use")
def ollama_prompt_cmd(text, model):
    """Prompt Ollama and get response."""
    response = _ollama.prompt(text, model)
    click.secho(response['response'], fg="green")


@cli.command("forge")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Ollama model to use")
@click.option("--avro2sql", metavar="AVRO_FILE", default=None,
              help="Convert an Avro schema to SQL DDL.")
@click.option("--output", type=click.Path(), default=None, help="Write output to file instead of stdout.")
def forge_cmd(model, avro2sql, output):
    """Run a schema conversion. Pass a conversion flag to select the type."""
    if avro2sql:
        if not Path(avro2sql).is_file():
            raise click.BadParameter(f"File '{avro2sql}' does not exist.", param_hint="--avro2sql")
        try:
            sql = avro_file_to_sql(avro2sql, model=model)
        except RuntimeError as exc:
            raise click.ClickException(str(exc))
        except Exception as exc:
            raise click.ClickException(f"Failed to process schema: {exc}")
        if output:
            with open(output, "w") as f:
                f.write(sql + "\n")
            click.echo(f"SQL written to {output}")
        else:
            click.echo(sql)
        return

    raise click.UsageError("Specify a conversion flag, e.g. --avro2sql AVRO_FILE.")


if __name__ == "__main__":
    cli()
