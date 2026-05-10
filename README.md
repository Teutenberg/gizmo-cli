# Gizmo

A CLI tool for managing project configuration and secrets.

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
