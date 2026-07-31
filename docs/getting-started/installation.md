# Installation

## Requirements

- Python 3.9 or newer
- Network access to `api.usaspending.gov`
- No USAspending API key

Install the released package:

```console
python -m pip install usaspending-orm
```

Or add it to a uv-managed project:

```console
uv add usaspending-orm
```

Verify the installation:

```python
import usaspending

print(usaspending.__version__)
```

## Development installation

Clone the repository and synchronize its locked environment:

```console
git clone https://github.com/planetary-society/usaspending-orm.git
cd usaspending-orm
uv sync --locked
```

Documentation dependencies are isolated in their own dependency group:

```console
uv sync --locked --group docs
uv run --group docs mkdocs serve
```

The released library supports Python 3.9+, while the documentation toolchain
requires Python 3.10+ and is built on Python 3.13 in Read the Docs.
