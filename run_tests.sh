#!/bin/bash

set -euo pipefail

echo -e "\nPytest:"
poetry run pytest tests ; echo Success!
echo -e "\nBandit:"
poetry run bandit -c pyproject.toml -r . ; echo Success!
echo -e "\nMypy:"
poetry run mypy . --show-error-codes --check-untyped-defs ; echo Success!
echo -e "\nFlake8:"
poetry run flake8  ; echo Success!
echo -e "\nPylint visclo:"
poetry run pylint  visclo; echo Success!
echo -e "\nPylint tests:"
poetry run pylint tests ; echo Success!

aspell check README.rst

echo -e "\nSUCCESS!"
