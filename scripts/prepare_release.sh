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

# uv builds the distribution artifacts in every mode and twine publishes
# them; check both upfront so a missing tool fails before any clone.
if ! command -v uv >/dev/null; then
    echo "uv is required to build the release artifacts; install it from https://docs.astral.sh/uv/ before releasing." >&2
    exit 1
fi
if ! command -v twine >/dev/null; then
    echo "twine is required to publish to PyPI; install it from https://twine.readthedocs.io/ before releasing." >&2
    exit 1
fi

version=$1
push_release=false
[[ $# -eq 2 ]] && push_release=true
if [[ "$push_release" == true ]] && ! command -v gh >/dev/null; then
    echo "gh is required for --push; install it from https://cli.github.com/ before releasing." >&2
    exit 1
fi
workdir=$(cd "$(mktemp -d /tmp/tg-release.XXXXXX)" && pwd)
trap 'if [[ "$retain_workdir" != true ]]; then rm -rf "$workdir"; fi' EXIT
retain_workdir=false
core="$workdir/tg2"
devtools="$workdir/tg2devtools"
docs="$workdir/tg2docs"
wheelhouse="$workdir/wheelhouse"
website="$workdir/tgwebsite"

git clone --branch development --single-branch git@github.com:TurboGears/tg2.git "$core"
git clone --branch development --single-branch git@github.com:TurboGears/tg2devtools.git "$devtools"
git clone --branch development --single-branch git@github.com:TurboGears/tg2docs.git "$docs"
git -C "$core" fetch origin master:refs/remotes/origin/master
git -C "$devtools" fetch origin master:refs/remotes/origin/master
git -C "$docs" fetch origin master:refs/remotes/origin/master

# Dev releases of X.Y.Z are covered by the "From ... to X.Y.Z" chapter.
upgrade_version=${version%.dev*}
upgrade_version=${upgrade_version%dev*}
if ! grep -Eq "^From .+ to ${upgrade_version//./\\.}$" "$docs/docs/reference/upgrading.rst"; then
    echo "docs/reference/upgrading.rst lacks a \"From ... to $upgrade_version\" chapter; add it to tg2docs before releasing." >&2
    exit 1
fi
core_development=$(git -C "$core" rev-parse origin/development)
devtools_development=$(git -C "$devtools" rev-parse origin/development)
docs_development=$(git -C "$docs" rev-parse origin/development)

core_version=$(sed -n 's/^version = "\([^"]*\)"$/\1/p' "$core/pyproject.toml")
devtools_version=$(sed -n 's/^version = "\([^"]*\)"$/\1/p' "$devtools/pyproject.toml")
if [[ -z "$core_version" || -z "$devtools_version" ]]; then
    echo "Could not read the current version from pyproject.toml in $core or $devtools." >&2
    exit 1
fi
if [[ "$core_version" != "$devtools_version" ]]; then
    echo "Project versions are not aligned: $core_version != $devtools_version" >&2
    exit 1
fi
sed -i "s/^version = \"$core_version\"$/version = \"$version\"/" "$core/pyproject.toml" "$devtools/pyproject.toml"
sed -i "s/TurboGears2 >= $core_version/TurboGears2 >= $version/" "$devtools/pyproject.toml" \
    "$devtools/devtools/gearbox/quickstart/template/pyproject.toml_tmpl" \
    "$devtools/devtools/gearbox/quickstart/template-api/pyproject.toml_tmpl"
# The change log section is generated from the commit history since the
# previous release, reviewed by the maintainer, and committed with the bump.
if ! prev_tag=$(git -C "$core" describe --tags --abbrev=0 --match 'tg*' HEAD); then
    echo "No previous tg* tag found in $core; cannot generate the change log section." >&2
    exit 1
fi
if grep -q "^== $version " "$core/CHANGES.txt"; then
    echo "CHANGES.txt already has a section for $version; remove it so the script can generate it." >&2
    exit 1
fi
section="$workdir/changelog_section.txt"
printf '\n== %s (**%s**) ==\n\n' "$version" "$(date '+%b %-d, %Y')" > "$section"
git -C "$core" log --no-merges --format="* %s" "$prev_tag..HEAD" >> "$section"
sed -i "/^= Change Log =$/r $section" "$core/CHANGES.txt"

for edited in "$core/pyproject.toml" "$devtools/pyproject.toml"; do
    grep -q "^version = \"$version\"$" "$edited" || { echo "Version was not updated in $edited." >&2; exit 1; }
done
for edited in "$devtools/pyproject.toml" \
    "$devtools/devtools/gearbox/quickstart/template/pyproject.toml_tmpl" \
    "$devtools/devtools/gearbox/quickstart/template-api/pyproject.toml_tmpl"; do
    grep -q "TurboGears2 >= $version" "$edited" || { echo "TurboGears2 dependency was not updated in $edited." >&2; exit 1; }
done
grep -q "^== $version " "$core/CHANGES.txt" || { echo "Changelog section for $version was not added to $core/CHANGES.txt." >&2; exit 1; }

echo "Review the new change log section for $version in $core/CHANGES.txt, then save and exit."
"${EDITOR:-vi}" "$core/CHANGES.txt"
grep -q "^== $version " "$core/CHANGES.txt" || { echo "The change log section for $version is missing from $core/CHANGES.txt; re-run the script and keep the section during review." >&2; exit 1; }
if ! awk -v v="^== $version " '/^== / { in_section = $0 ~ v; next } in_section && NF { filled = 1 } END { exit !filled }' "$core/CHANGES.txt"; then
    echo "The change log section for $version is empty; re-run the script and fill the section during review." >&2
    exit 1
fi

python -m venv "$workdir/venv"
python_bin="$workdir/venv/bin/python"
mkdir "$wheelhouse"
# uv builds the wheels that get installed and tested together with the sdists
# that get uploaded, so the wheelhouse holds the exact published artifacts.
uv build --out-dir "$wheelhouse" "$core"
uv build --out-dir "$wheelhouse" "$devtools"
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

# Docs have no version to bump, so they get no release commit; the annotated
# tag alone triggers the workflow that publishes the versioned text docs.
git -C "$docs" checkout -B master origin/master
git -C "$docs" merge --ff-only development
git -C "$docs" tag -a "tg$version" -m "Release $version"
git -C "$docs" checkout development

if [[ "$push_release" == true ]]; then
    # Check every remote before publishing any repository.
    for repo in "$core" "$devtools" "$docs"; do
        remote_master=$(git -C "$repo" ls-remote --heads origin refs/heads/master | cut -f1)
        local_master=$(git -C "$repo" rev-parse origin/master)
        if [[ "$remote_master" != "$local_master" ]]; then
            echo "Remote master changed during release testing in $repo; aborting." >&2
            exit 1
        fi
        expected_development=$core_development
        [[ "$repo" == "$devtools" ]] && expected_development=$devtools_development
        [[ "$repo" == "$docs" ]] && expected_development=$docs_development
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
    for repo in "$core" "$devtools" "$docs"; do
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

    # All tags are published; generate notes and let maintainers curate
    # them on GitHub afterwards. Docs get no GitHub release.
    failed_repos=()
    for github_repo in TurboGears/tg2 TurboGears/tg2devtools; do
        if ! gh release create "tg$version" --title "Version $version" --generate-notes --repo "$github_repo"; then
            failed_repos+=("$github_repo")
            echo "GitHub release creation failed for $github_repo; the tag tg$version was already pushed." >&2
            echo "Create it manually with: gh release create \"tg$version\" --title \"Version $version\" --generate-notes --repo $github_repo" >&2
        fi
    done
    if ((${#failed_repos[@]})); then
        retain_workdir=true
        echo "PyPI upload and the website update were not performed; the release artifacts are kept in $wheelhouse." >&2
        echo "After creating the missing release(s), publish them with: twine upload \"$wheelhouse\"/*" >&2
        exit 1
    fi

    # Both GitHub releases exist; publish the already tested artifacts.
    if ! twine upload "$wheelhouse"/*; then
        retain_workdir=true
        echo "twine upload failed; the workdir with the artifacts is kept at $workdir." >&2
        echo "Retry manually with: twine upload \"$wheelhouse\"/*" >&2
        exit 1
    fi

    # PyPI's index can lag behind a successful upload, so wait until both
    # projects list the version before advertising it on the website.
    if ! "$python_bin" - "$version" <<'PY'
import http.client
import json
import sys
import time
import urllib.error
import urllib.request

from packaging.utils import canonicalize_version

# PyPI keys releases by the canonicalized version, so 2.5.1dev1 is listed as 2.5.1.dev1.
version = canonicalize_version(sys.argv[1])
for attempt in range(20):
    pending = []
    for project in ("TurboGears2", "tg.devtools"):
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{project}/json", timeout=30) as response:
                listed = version in {canonicalize_version(release) for release in json.load(response)["releases"]}
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException, ValueError):
            # Read-phase timeouts and truncated or invalid bodies are not URLError
            # subclasses; any failed fetch counts as pending and is retried.
            listed = False
        if not listed:
            pending.append(project)
    if not pending:
        sys.exit(0)
    if attempt < 19:
        time.sleep(15)
print(f"PyPI has not listed {version} for: {', '.join(pending)}", file=sys.stderr)
sys.exit(1)
PY
    then
        retain_workdir=true
        echo "Upload succeeded, but PyPI does not list $version yet (or could not be reached); the website was NOT updated." >&2
        echo "Once PyPI lists $version, update the website manually: clone git@github.com:TurboGears/tgwebsite.git, update the version and release date in src/current-status.rst and the version in src/themes/w3/layout.html, commit \"Release $version\" and push origin master." >&2
        exit 1
    fi

    # The website advertises the latest stable release; dev releases skip it.
    if [[ "$version" == *dev* ]]; then
        echo "Development release; the website was not updated." >&2
    else
        # Any failure here leaves a fully published release, so keep the clone
        # for manual fixing instead of losing the remaining work. The subshell
        # runs in a tested context where set -e is ignored, hence || exit 1.
        if ! (
            git clone --branch master --single-branch git@github.com:TurboGears/tgwebsite.git "$website" || exit 1
            # The previous release is read from the status page so the announcement and
            # download box keep pointing at consistent versions.
            status="$website/src/current-status.rst"
            layout="$website/src/themes/w3/layout.html"
            previous=$(sed -n 's/^Latest stable release: \([^ ]*\) — released .\+$/\1/p' "$status") || exit 1
            [[ -n "$previous" ]] || { echo "Latest stable release line not found in $status." >&2; exit 1; }
            sed -i "s/^Latest stable release: $previous — released .*$/Latest stable release: $version — released $(date '+%B %-d, %Y')/" "$status" || exit 1
            sed -i "s|releases/tag/tg$previous|releases/tag/tg$version|" "$status" "$layout" || exit 1
            sed -i "s|>$previous</a>|>$version</a>|" "$layout" || exit 1
            grep -q "^Latest stable release: $version — released" "$status" || { echo "Latest stable release line was not updated in $status." >&2; exit 1; }
            grep -q "releases/tag/tg$version" "$status" || { echo "Release link was not updated in $status." >&2; exit 1; }
            grep -q "releases/tag/tg$version" "$layout" || { echo "Release link was not updated in $layout." >&2; exit 1; }
            grep -q ">$version</a>" "$layout" || { echo "Download box version was not updated in $layout." >&2; exit 1; }
            git -C "$website" add src/current-status.rst src/themes/w3/layout.html || exit 1
            git -C "$website" commit -m "Release $version" || exit 1
            # Pushes to master auto-deploy GitHub Pages.
            git -C "$website" push origin master || exit 1
        ); then
            retain_workdir=true
            echo "Release $version is fully published, but the website was not updated." >&2
            if [[ -d "$website" ]]; then
                echo "The clone at $website is kept for manual fixing; fix any partially edited files, then run: git -C $website add src/current-status.rst src/themes/w3/layout.html && git -C $website commit -m \"Release $version\" || true; git -C $website push origin master" >&2
            else
                echo "Re-create the clone with: git clone --branch master --single-branch git@github.com:TurboGears/tgwebsite.git $website" >&2
                echo "Then update the version and release date in src/current-status.rst and the version in src/themes/w3/layout.html, commit \"Release $version\" and push origin master." >&2
            fi
            exit 1
        fi
    fi
else
    retain_workdir=true
    printf 'Prepared release retained at: %s\n' "$workdir"
    for repo in "$core" "$devtools" "$docs"; do
        printf '%s master=%s development=%s tg%s=%s\n' \
            "$(basename "$repo")" \
            "$(git -C "$repo" rev-parse refs/heads/master)" \
            "$(git -C "$repo" rev-parse refs/heads/development)" \
            "$version" "$(git -C "$repo" rev-parse "refs/tags/tg$version^{commit}")"
    done
fi
