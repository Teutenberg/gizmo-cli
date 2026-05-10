import json
import urllib.request
import urllib.error
from pathlib import Path
import yaml
from .ollama import ollama_host, ollama_model, ollama_timeout


DEFAULT_MODEL = "qwen2.5:3b"

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> tuple[str, str]:
    """Load system and prompt template from a YAML prompt file."""
    data = yaml.safe_load((_PROMPTS_DIR / name).read_text())
    return data["system"].strip(), data["prompt"].strip()


def _avro_to_sql_prompt(avro_schema: dict) -> tuple[str, str]:
    system, prompt_template = _load_prompt("avro2sql.yaml")
    return system, prompt_template.format(schema=json.dumps(avro_schema, indent=2))


def avro_file_to_sql(path: str, model: str | None = None) -> str:
    """Load an Avro schema from a file path and return SQL DDL."""
    with open(path) as f:
        schema = json.load(f)
    return avro_schema_to_sql(schema, model=model)


def avro_schema_to_sql(avro_schema: dict | str, model: str | None = None) -> str:
    """Send an Avro schema to a local Ollama model and return SQL DDL."""
    if isinstance(avro_schema, str):
        avro_schema = json.loads(avro_schema)

    target_model = model or ollama_model()
    url = f"{ollama_host()}/api/generate"

    system, prompt = _avro_to_sql_prompt(avro_schema)
    payload = json.dumps({
        "model": target_model,
        "system": system,
        "prompt": prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=ollama_timeout()) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach Ollama at {url}. Is it running? ({exc})"
        ) from exc
