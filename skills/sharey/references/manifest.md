# Node manifest

`schema_version` is 1. Required fields are `title`, `summary`, `contributor`, `memory` and `files`. `parents`, `sources` and `skills` default to empty arrays. The JSON template is at `../assets/node-manifest.json`.

`memory` and every file `source` resolve relative to the manifest's directory. Sources may be explicitly selected from elsewhere; they must be regular files, with no symbolic links in their paths. Each `path` is the file's destination under the node's `files/` directory. Use normalized relative POSIX paths with no empty, dot or parent components, backslashes, colons or control characters. List files individually; directory recursion is only for complete Skill publication. Duplicate destinations fail.

The CLI compiles provenance from the bytes it actually read. When Git is available, it records a baseline commit and whether each selected file is clean, modified or untracked relative to that baseline. It does not publish remote URLs, modify the source repository or infer research parents from source commits. A client without Git can still publish.

Parent IDs must be already published research nodes in this project. Source and Skill IDs must be already published objects of the matching type in this project. A combined node lists both branch IDs in `parents`; its files are an explicit new snapshot, without implicit inheritance of parent files.
