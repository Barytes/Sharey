---
name: sharey
description: Publish explicitly selected research materials and memory to a Sharey project; find, cite and continue published research nodes, sources and complete Skills through the Sharey CLI.
---

Use the installed `sharey` CLI. The member supplies `SHAREY_URL`, `SHAREY_PROJECT` and `SHAREY_TOKEN` in the environment, or the corresponding global options. Keep the credential out of shared files and command output.

## Read and continue

1. Run `sharey overview`. Locate the research goal, relevant nodes and their parents, source materials and Skills.
2. Run `sharey show node <id>` for the relevant nodes. Read their research memory and file list; follow parents or asset references when needed. Access remains project-wide after downloading one node.
3. Download only what the task needs with `sharey get file <node-id> <path> --out <new-file>` or `sharey get node <id> --out <new-dir>`. Use an explicit new destination.
4. Answer from the retrieved evidence. Cite the project, node ID and file path for substantive claims; distinguish observations, assumptions and the next untested step. A useful citation is `project / node-id / files/path` accompanied by the corresponding `sharey show` or `sharey get` command.
5. For Skill reuse, run `sharey show skill <id>` and `sharey get skill <id> --out <new-dir>`. Read its `SKILL.md` and the resources it calls for. Inspect downloaded scripts and follow the member's task authorization before executing. Resolve resources relative to the downloaded Skill; verify exit status and actual output. Downloading alone does not prove execution.

For the complete command interface and error handling, read [references/cli.md](references/cli.md).

## Compile and publish

1. Determine what the member has authorized sharing to this project. Use that scope to select exact files and relevant research memory. If sharing scope is missing, clarify it before publishing; an existing explicit scope authorizes the work within it.
2. Write a standalone Markdown memory containing the goal, evidence-backed progress, constraints, open questions and the next step. Include enough context for a new Agent without the original chat. Keep unrelated private memory local.
3. Build a version 1 JSON manifest from [assets/node-manifest.json](assets/node-manifest.json). List exact source-to-destination file mappings, contributor, title, short summary, and existing project node/source/Skill IDs. Read [references/manifest.md](references/manifest.md) when constructing the manifest.
4. Publish referenced assets first when needed: `sharey publish source --file <file> --title <title> --contributor <name> --key <key>` and `sharey publish skill --dir <complete-dir> --title <title> --contributor <name> --key <key>`. A Skill publication selects its entire directory, including scripts, references, templates and assets; review that complete selection.
5. Run `sharey publish node --manifest <manifest> --key <key>`. Selected files are captured from their current disk bytes, including uncommitted or untracked work. Source repository history is provenance; `parents` are Sharey research node IDs.
6. Check the returned ID with `sharey show node <id>` and `sharey overview`. Report exactly what became shared and cite the resulting node and assets. Continue editing the original working files normally; a subsequent publication is a new immutable node.

Reuse a request key only to retry the same publication after an uncertain response. Changed content needs a new key. A 409 means the old key already identifies different content; inspect the original publication and use a new key for a revision.

## Branch and combine

To continue one result, publish a new node with that node in `parents`. For a combined result, read both branches, synthesize the findings and selected files explicitly, then publish with both node IDs in `parents`. Sharey records the exact multi-parent relationship; the publishing Agent supplies the combined research content. Verify both parents in the returned node and overview.
