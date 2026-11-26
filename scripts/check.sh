#!/usr/bin/env bash
# Run the same checks locally and in CI; generated output stays outside site/.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Optional machine-local runtime setup; dependencies stay outside Git.
if [[ -f .tools/env.sh ]]; then
  source .tools/env.sh
fi
if [[ -z "${PYTHON:-}" ]]; then
  if [[ -x .venv/bin/python ]]; then
    PYTHON=.venv/bin/python
  else
    PYTHON=python3
  fi
fi
export BUNDLE_GEMFILE="$PWD/site/Gemfile"
"$PYTHON" -m unittest discover -s tests
node --test tests/search.test.cjs
bundle exec jekyll build --source site --destination _site --strict_front_matter
"$PYTHON" scripts/verify_media.py --site _site
"$PYTHON" scripts/verify_site.py --site _site --repeat
