---
name: pilot-summary
description: Summarize the fixed two-variant pilot latency CSV using the supplied protocol, configuration and report template.
---

Read [references/protocol.md](references/protocol.md). Run the script from any working directory:

```sh
python3 /path/to/this-skill/scripts/summarize.py --input /path/to/pilot.csv --out /path/to/new-results
```

The script reads `assets/config.json` and `templates/report.md` relative to this Skill directory. It writes `results.json` and `report.md` into a new output directory. Check both files and the exit status. Cite the source node and data path; describe the result as a fixed pilot observation and propose a randomized measurement follow-up.
