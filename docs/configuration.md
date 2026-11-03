# Project configuration

Back to the [README](../README.md).

## `.gauntlet.json`

Each project describes itself in a `.gauntlet.json` at its root, so the agents carry no project specifics. ControlTower's (`examples/controltower.gauntlet.json`):

```json
{
  "integration_branch": "feat/decision-tree",
  "shared": ["node_modules"],
  "checks": [
    {"name": "test", "command": "npx vitest run"},
    {"name": "build:ts", "command": "npm run build:ts"},
    {"name": "build:app", "command": "npm run build:app"},
    {"name": "typecheck", "command": "npx tsc --noEmit -p src/renderer"}
  ],
  "setup": "npm run rebuild:node"
}
```

| Field | Type | Default | Meaning |
|---|---|---|---|
| `integration_branch` | string, required | none | The branch slices are cut from and merged into. `loop_start` can override it per loop. |
| `shared` | list of relative paths | `[]` | Folders in the integration worktree to symlink into each slice worktree, such as `node_modules`. No absolute paths and no `..`. |
| `checks` | list of `{"name", "command"}` | `[]` | The commands every slice must pass. Each entry has exactly these two non-empty strings. |
| `setup` | string or `null` | `null` | A command to run once before a loop. |

Any other key is an error. The server reports errors by field (`config_invalid` with `fields`). To check a file, run `gauntlet config <repo>`.

Shared folders are linked from the integration worktree and kept out of git through the repository's common `info/exclude` (found with `git rev-parse --git-path info/exclude`), using an anchored entry such as `/node_modules`. The project's `.gitignore` is never edited.

If a project has no `.gauntlet.json`, `loop_start` refuses with `config_missing` and lists the four fields. epsilon then asks you for them and offers to write the file. It doesn't commit the file.
