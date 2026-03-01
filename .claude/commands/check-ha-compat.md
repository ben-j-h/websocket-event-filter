Check if the `websocket-event-filter` monkey patch is compatible with a Home Assistant version.

**Usage:** `/check-ha-compat [branch-or-tag]` — defaults to `dev` if no argument given.

The argument provided by the user (if any) is: $ARGUMENTS

---

You are checking whether the `websocket-event-filter` custom component's monkey patch is compatible with a given Home Assistant version. Follow these steps exactly.

## Step 1: Determine the ref to check

If `$ARGUMENTS` is empty or whitespace, use `dev`. Otherwise use `$ARGUMENTS` as the ref (branch, tag like `2025.6.0`, or commit SHA). Call this `HA_REF`.

## Step 2: Fetch the target file

Run this Bash command to fetch the file content (substitute the actual ref value for `HA_REF`):

```bash
gh api "repos/home-assistant/core/contents/homeassistant/components/websocket_api/commands.py?ref=HA_REF" \
  --jq '.content' | base64 -d 2>&1
```

Also capture the latest commit info on that ref:

```bash
gh api "repos/home-assistant/core/commits?sha=HA_REF&per_page=1" \
  --jq '.[0] | {sha: .sha[0:7], date: .commit.committer.date}' 2>&1
```

If `gh` returns an auth error (e.g., "not logged into any GitHub host"), stop and report:
> Error: `gh` is not authenticated. Run `gh auth login` and try again.

If the file is not found (HTTP 404), report:
> BREAKING CHANGE: `homeassistant/components/websocket_api/commands.py` was NOT FOUND at ref `HA_REF`.
> The file may have moved. The monkey patch cannot be applied without updating the module path in `__init__.py`.
>
> To find where the functions moved, try:
> ```bash
> gh api "repos/home-assistant/core/contents/homeassistant/components/websocket_api?ref=HA_REF" --jq '.[].name'
> ```

Then stop.

## Step 3: Extract function signatures

From the downloaded source, for each of these three functions find the `def FUNCTION_NAME(` line and extract the ordered list of parameter names (everything between the opening `(` and the closing `) -> None:`, which may span multiple lines). Exclude type annotations — keep only the bare parameter names.

Functions to check:
- `_forward_events_check_permissions`
- `_forward_events_unconditional`
- `_forward_entity_changes`

If a function is not found in the source at all, record it as MISSING.

## Step 4: Compare against expected signatures

The expected parameter lists are:

```
_forward_events_check_permissions : [send_message, user, message_id_as_bytes, event]
_forward_events_unconditional     : [send_message, message_id_as_bytes, event]
_forward_entity_changes           : [send_message, entity_ids, entity_filter, user, message_id_as_bytes, event]
```

For each function compare the actual parameter names (in order) against the expected list.

## Step 5: Report results

Print a report in this exact format:

```
=== HA Compatibility Check ===
Ref checked : HA_REF
Commit      : <sha> (<date>)
File        : homeassistant/components/websocket_api/commands.py  FOUND ✓
──────────────────────────────────────────────────────────────────

_forward_events_check_permissions
  Expected : [send_message, user, message_id_as_bytes, event]
  Actual   : [<actual params>]
  Result   : COMPATIBLE ✓

_forward_events_unconditional
  Expected : [send_message, message_id_as_bytes, event]
  Actual   : [<actual params>]
  Result   : COMPATIBLE ✓

_forward_entity_changes
  Expected : [send_message, entity_ids, entity_filter, user, message_id_as_bytes, event]
  Actual   : [<actual params>]
  Result   : COMPATIBLE ✓

──────────────────────────────────────────────────────────────────
OVERALL: Patch is compatible — safe to upgrade.
```

Use `BREAKING CHANGE ✗` instead of `COMPATIBLE ✓` for any function that is missing or has a changed signature. For OVERALL use either "Patch is compatible — safe to upgrade." or "Patch needs update — breaking changes detected (see below)."

For a MISSING function show:
```
  Actual   : MISSING — function not found in source
  Result   : BREAKING CHANGE ✗
```

## Step 6: If breaking changes detected

For each function with a changed or missing signature, provide specific remediation guidance:

**If parameter order or names changed:** Show the old wrapper call vs. the new wrapper call that would be needed in `__init__.py`. The wrappers are closures that call `original(send_message, ...)` — they must pass positional arguments in the correct order.

**If a parameter was added:** Show what the updated wrapper function definition should look like to accept and pass through the new parameter.

**If the function is missing:** Suggest searching for where the forwarding logic moved:
```bash
gh api "repos/home-assistant/core/search/code?q=send_message+cached_state_diff_message+repo:home-assistant/core" --jq '.items[].path' 2>&1
```

Be specific — show the exact lines that need to change in `__init__.py`.
