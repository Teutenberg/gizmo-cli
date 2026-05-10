# Gizmo

A CLI tool for managing project configuration, secrets, local Ollama models, and schema conversions.

## Installation

```sh
sh install.sh && source ~/.bashrc
```

## Usage

### Initialize

Set up Gizmo in the current directory:

```sh
gizmo init --database mydb --schema myschema
```

### Config

Manage values in `.gizmo/config.yaml`:

```sh
gizmo config list              # list all config values
gizmo config list mykey        # get a single value
gizmo config set mykey myvalue # set a value (keys prefixed with secret_ are encrypted)
gizmo config unset mykey       # remove a value
```

### Secrets

Manage secrets stored in the system keyring:

```sh
gizmo secret list              # list all secret keys
gizmo secret set               # store a secret (prompted for name and value)
gizmo secret delete mykey      # delete a secret
gizmo secret rotate_key        # rotate the encryption key
```

Secrets stored via `gizmo secret set` are kept in the OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Manager) and never written to disk in plaintext.

### Ollama

Manage a local [Ollama](https://ollama.com) installation:

```sh
gizmo ollama install           # install Ollama locally (no sudo required)
gizmo ollama install --system  # install using the official script (requires sudo)
gizmo ollama run               # start the Ollama server in the background
gizmo ollama run --wait        # start and wait until the server is reachable
gizmo ollama pull              # pull the model configured in config
gizmo ollama pull llama3       # pull a specific model
gizmo ollama status            # show host, configured model, and running state
```

### Forge

Run AI-assisted schema conversions using a local Ollama model:

```sh
gizmo forge --avro2sql schema.avsc          # convert an Avro schema to SQL DDL
gizmo forge --avro2sql schema.avsc --output out.sql  # write output to a file
gizmo forge --avro2sql schema.avsc --model mistral   # use a specific model
```
