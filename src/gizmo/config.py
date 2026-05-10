from pathlib import Path
from jinja2 import Environment, FileSystemLoader, meta
import yaml
from .secret import encrypt


CONFIG_PATH = Path(".gizmo")
CONFIG_FILE = CONFIG_PATH / "config.yaml"
CONFIG_TEMPLATE = "config.yaml.jinja"


def _load() -> dict:
    if not CONFIG_FILE.exists():
        click.echo("Path has not been initialized with 'gizmo init'.")
        return
    with CONFIG_FILE.open() as f:
        return yaml.safe_load(f) or {}


def _save(data: dict) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_FILE.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _get_nested(data: dict, parts: list[str]):
    for part in parts:
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def _set_nested(data: dict, parts: list[str], value) -> None:
    for part in parts[:-1]:
        data = data.setdefault(part, {})
    data[parts[-1]] = value


def _unset_nested(data: dict, parts: list[str]) -> None:
    for part in parts[:-1]:
        if not isinstance(data, dict) or part not in data:
            return
        data = data[part]
    data.pop(parts[-1], None)


def _flatten_keys(data: dict, prefix: str = "") -> set[str]:
    keys = set()
    for k, v in data.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten_keys(v, full)
        else:
            keys.add(full)
    return keys


def _flatten_items(data: dict, prefix: str = "") -> dict:
    items = {}
    for k, v in data.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items |= _flatten_items(v, full)
        else:
            items[full] = v
    return items


def config_keys(TEMPLATE_PATH: Path) -> set[str]:
    env = Environment(loader=FileSystemLoader(TEMPLATE_PATH), keep_trailing_newline=True)
    variables = meta.find_undeclared_variables(env.parse(env.loader.get_source(env, CONFIG_TEMPLATE)[0]))
    placeholder = {var: "__placeholder__" for var in variables}
    rendered = env.get_template(CONFIG_TEMPLATE).render(**placeholder)
    return _flatten_keys(yaml.safe_load(rendered))


def config_init(TEMPLATE_PATH: Path, context: dict) -> None:
    env = Environment(loader=FileSystemLoader(TEMPLATE_PATH), keep_trailing_newline=True)
    template = env.get_template(CONFIG_TEMPLATE)
    rendered = template.render(**context)
    CONFIG_PATH.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(rendered)


def config_list() -> dict:
    return _flatten_items(_load())


def config_get(key: str):
    return _get_nested(_load(), key.split("."))


def config_set(TEMPLATE_PATH: Path, key: str, value: str) -> None:
    if key not in config_keys(TEMPLATE_PATH):
        raise KeyError(key)
    data = _load()
    parts = key.split(".")
    coerced = encrypt(value) if parts[-1].startswith("secret_") else yaml.safe_load(value)
    _set_nested(data, parts, coerced)
    _save(data)


def config_unset(key: str) -> None:
    data = _load()
    _unset_nested(data, key.split("."))
    _save(data)
