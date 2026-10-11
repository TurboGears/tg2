#!/usr/bin/env bash
set -euo pipefail

if (( $# < 1 || $# > 2 )); then
    echo "Usage: $0 MAJOR.MINOR.PATCH[.devN] [--push]" >&2
    exit 2
fi
if [[ ! $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+(\.?dev[0-9]+)?$ ]] || { (( $# == 2 )) && [[ $2 != --push ]]; }; then
    echo "Usage: $0 MAJOR.MINOR.PATCH[.devN] [--push]" >&2
    exit 2
fi

version=$1
push_release=false
[[ $# -eq 2 ]] && push_release=true
workdir=$(cd "$(mktemp -d /tmp/tg-release.XXXXXX)" && pwd)
trap 'if [[ "$push_release" == true || "$retain_workdir" != true ]]; then rm -rf "$workdir"; fi' EXIT
retain_workdir=false
core="$workdir/tg2"
devtools="$workdir/tg2devtools"
wheelhouse="$workdir/wheelhouse"

git clone --branch development --single-branch git@github.com:TurboGears/tg2.git "$core"
git clone --branch development --single-branch git@github.com:TurboGears/tg2devtools.git "$devtools"
git -C "$core" fetch origin master:refs/remotes/origin/master
git -C "$devtools" fetch origin master:refs/remotes/origin/master
core_development=$(git -C "$core" rev-parse origin/development)
devtools_development=$(git -C "$devtools" rev-parse origin/development)

python - "$version" "$core" "$devtools" <<'PY'
from datetime import date
from pathlib import Path
import re
import sys

version, core, devtools = sys.argv[1:]
core = Path(core)
devtools = Path(devtools)

def replace_once(text, old, new, path):
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one {old!r} in {path}")
    return text.replace(old, new, 1)


metadata = core / "pyproject.toml"
text = metadata.read_text()
core_version = re.search(r'(?m)^version = "([^"]+)"$', text).group(1)

metadata = devtools / "pyproject.toml"
devtools_text = metadata.read_text()
devtools_version = re.search(r'(?m)^version = "([^"]+)"$', devtools_text).group(1)
if core_version != devtools_version:
    raise ValueError(f"Project versions are not aligned: {core_version} != {devtools_version}")

text = replace_once(text, f'version = "{core_version}"', f'version = "{version}"', core / "pyproject.toml")
(core / "pyproject.toml").write_text(text)

changelog = core / "CHANGES.txt"
text = replace_once(changelog.read_text(), "= Change Log =\n", f"= Change Log =\n\n== {version} (**{date.today():%b %-d, %Y}**) ==\n", changelog)
changelog.write_text(text)

text = replace_once(devtools_text, f'version = "{devtools_version}"', f'version = "{version}"', metadata)
text = replace_once(text, f'TurboGears2 >= {core_version}', f'TurboGears2 >= {version}', metadata)
metadata.write_text(text)

for template in (
    devtools / "devtools/gearbox/quickstart/template/pyproject.toml_tmpl",
    devtools / "devtools/gearbox/quickstart/template-api/pyproject.toml_tmpl",
):
    text = replace_once(template.read_text(), f"TurboGears2 >= {core_version}", f"TurboGears2 >= {version}", template)
    template.write_text(text)
PY

python -m venv "$workdir/venv"
python_bin="$workdir/venv/bin/python"
mkdir "$wheelhouse"
"$python_bin" -m pip wheel --no-deps --wheel-dir "$wheelhouse" "$core"
"$python_bin" -m pip wheel --no-deps --wheel-dir "$wheelhouse" "$devtools"
shopt -s nullglob
core_wheels=("$wheelhouse"/turbogears2-*.whl)
devtools_wheels=("$wheelhouse"/tg_devtools-*.whl)
if ((${#core_wheels[@]} != 1)); then
    echo "Expected exactly one TurboGears2 wheel in $wheelhouse, found ${#core_wheels[@]}." >&2
    exit 1
fi
if ((${#devtools_wheels[@]} != 1)); then
    echo "Expected exactly one tg.devtools wheel in $wheelhouse, found ${#devtools_wheels[@]}." >&2
    exit 1
fi
"$python_bin" -m pip install "${core_wheels[0]}" "${devtools_wheels[0]}"
expected_version=$(
    "$python_bin" -c 'from importlib.metadata import version; print(version("TurboGears2"))'
)
"$python_bin" -m pip install packaging kajiki genshi jinja2 mako pytest WebTest

(
    cd "$workdir"
    export TG_TEST_DEPENDENCIES=pypi
    export PRESERVE_TEST_ARTIFACTS=1
    export PIP_FIND_LINKS="$wheelhouse"
    "$python_bin" -m pytest "$devtools/devtools/tests"
)
actual_version=$(
    "$workdir/TESTENV/bin/python" -c 'from importlib.metadata import version; print(version("TurboGears2"))'
)
if ! "$python_bin" -c 'import sys; from packaging.version import Version; sys.exit(Version(sys.argv[1]) != Version(sys.argv[2]))' "$actual_version" "$expected_version"; then
    echo "Quickstart installed TurboGears2 $actual_version; expected $expected_version." >&2
    exit 1
fi
printf 'Verified quickstart TurboGears2 version: %s\n' "$actual_version"

for repo in "$core" "$devtools"; do
    git -C "$repo" add pyproject.toml
    if [[ "$repo" == "$core" ]]; then
        git -C "$repo" add CHANGES.txt
    else
        git -C "$repo" add devtools/gearbox/quickstart/template/pyproject.toml_tmpl \
            devtools/gearbox/quickstart/template-api/pyproject.toml_tmpl
    fi
    git -C "$repo" commit -m "Release $version"
    git -C "$repo" checkout -B master origin/master
    git -C "$repo" merge --ff-only development
    git -C "$repo" tag -a "tg$version" -m "Release $version"
    git -C "$repo" checkout development
done

if [[ "$push_release" == true ]]; then
    # Check both remotes before publishing either repository.
    for repo in "$core" "$devtools"; do
        remote_master=$(git -C "$repo" ls-remote --heads origin refs/heads/master | cut -f1)
        local_master=$(git -C "$repo" rev-parse origin/master)
        if [[ "$remote_master" != "$local_master" ]]; then
            echo "Remote master changed during release testing in $repo; aborting." >&2
            exit 1
        fi
        expected_development=$core_development
        [[ "$repo" == "$devtools" ]] && expected_development=$devtools_development
        remote_development=$(git -C "$repo" ls-remote --heads origin refs/heads/development | cut -f1)
        if [[ "$remote_development" != "$expected_development" ]]; then
            echo "Remote development changed during release testing in $repo; aborting." >&2
            exit 1
        fi
        if [[ -n $(git -C "$repo" ls-remote origin "refs/tags/tg$version" "refs/tags/tg$version^{}") ]]; then
            echo "Release tag tg$version already exists in $repo; aborting." >&2
            exit 1
        fi
    done

    published_repos=()
    for repo in "$core" "$devtools"; do
        if ! git -C "$repo" push --atomic origin master development "tg$version"; then
            echo "Atomic push failed for $(basename "$repo"); verify its remote refs before retrying." >&2
            if ((${#published_repos[@]})); then
                printf 'Already published: %s\n' "${published_repos[*]}" >&2
                echo "Release is partial; publish the remaining repository before retrying." >&2
            fi
            exit 1
        fi
        published_repos+=("$(basename "$repo")")
    done
else
    retain_workdir=true
    printf 'Prepared release retained at: %s\n' "$workdir"
    for repo in "$core" "$devtools"; do
        printf '%s master=%s development=%s tg%s=%s\n' \
            "$(basename "$repo")" \
            "$(git -C "$repo" rev-parse refs/heads/master)" \
            "$(git -C "$repo" rev-parse refs/heads/development)" \
            "$version" "$(git -C "$repo" rev-parse "refs/tags/tg$version^{commit}")"
    done
fi
