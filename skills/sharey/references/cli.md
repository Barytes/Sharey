# CLI reference

Global connection options precede the command: `sharey --url <url> --project <project> --token <token> ...`. Prefer environment variables so the credential is not in shell history.

| Task | Command |
| --- | --- |
| Project navigation | `sharey overview` |
| Object index | `sharey list nodes`, `sharey list sources`, `sharey list skills` |
| Read object | `sharey show node <id>`, `sharey show source <id>`, `sharey show skill <id>` |
| Raw selected file | `sharey get file <node-id> <relative-path> --out <new-file>` |
| Node snapshot | `sharey get node <id> --out <new-directory>` |
| Original source | `sharey get source <id> --out <new-file>` |
| Complete Skill | `sharey get skill <id> --out <new-directory>` |
| Publish node | `sharey publish node --manifest <json> --key <request-key>` |
| Publish source | `sharey publish source --file <path> --title <title> --summary <summary> --contributor <name> --key <request-key>` |
| Publish Skill | `sharey publish skill --dir <directory> --title <title> --summary <summary> --contributor <name> --key <request-key>` |

Success prints JSON, including stable publication IDs. Failures return a nonzero exit code and an explanation on stderr. Existing output destinations are rejected; choose a new destination. Missing files, malformed manifests and nonregular inputs fail before publication. Invalid references and unsafe archives fail without a new visible publication. 401 means the project credential is missing or wrong; obtain the intended project credential from the member. 413 means the configured service limit was exceeded; reduce the explicitly selected package or ask the deployer to adjust the limit.

Keys use 1–128 ASCII letters, digits, dots, underscores or hyphens. Keep a key with the manifest for uncertain-response retries. No client Git installation, clone, commit or global Skill installation is required.
