import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

from sharey.client import pack_node, pack_skill, pack_source, save_archive, save_file
from sharey.errors import ShareyError


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="sharey")
    result.add_argument("--url", default=os.environ.get("SHAREY_URL"))
    result.add_argument("--project", default=os.environ.get("SHAREY_PROJECT"))
    result.add_argument("--token", default=os.environ.get("SHAREY_TOKEN"))
    commands = result.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the self-hosted service")
    serve.add_argument("--config", type=Path, required=True)
    serve.add_argument("--data-dir", type=Path, required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    commands.add_parser("overview", help="Read project navigation")
    listing = commands.add_parser("list", help="List published objects")
    listing.add_argument("kind", choices=["nodes", "sources", "skills"])
    show = commands.add_parser("show", help="Read a publication")
    show.add_argument("kind", choices=["node", "source", "skill"])
    show.add_argument("id")
    get = commands.add_parser("get", help="Download to a new destination")
    get.add_argument("kind", choices=["node", "file", "source", "skill"])
    get.add_argument("id")
    get.add_argument("path", nargs="?")
    get.add_argument("--out", type=Path, required=True)
    publish = commands.add_parser("publish", help="Publish selected files")
    publications = publish.add_subparsers(dest="kind", required=True)
    node = publications.add_parser("node")
    node.add_argument("--manifest", type=Path, required=True)
    node.add_argument("--key", required=True)
    source = publications.add_parser("source")
    source.add_argument("--file", type=Path, required=True)
    source.add_argument("--title", required=True)
    source.add_argument("--summary", default="")
    source.add_argument("--contributor", required=True)
    source.add_argument("--key", required=True)
    skill = publications.add_parser("skill")
    skill.add_argument("--dir", type=Path, required=True)
    skill.add_argument("--title", required=True)
    skill.add_argument("--summary", default="")
    skill.add_argument("--contributor", required=True)
    skill.add_argument("--key", required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "serve":
            import uvicorn

            from sharey.server import create_app

            config = json.loads(args.config.read_text(encoding="utf-8"))
            uvicorn.run(create_app(args.data_dir, config), host=args.host, port=args.port)
            return 0
        if not all((args.url, args.project, args.token)):
            raise ValueError("Set SHAREY_URL, SHAREY_PROJECT and SHAREY_TOKEN or global options")
        method, content = "GET", None
        headers = {"Authorization": f"Bearer {args.token}"}
        if args.command == "overview":
            endpoint = "overview"
        elif args.command == "list":
            endpoint = args.kind
        elif args.command == "publish":
            endpoint, method = args.kind + "s", "POST"
            if args.kind == "node":
                content = pack_node(args.manifest)
            elif args.kind == "source":
                content = pack_source(args.file, args.title, args.summary, args.contributor)
            else:
                content = pack_skill(args.dir, args.title, args.summary, args.contributor)
            headers.update({"Content-Type": "application/zip", "Idempotency-Key": args.key})
        elif args.command == "show":
            endpoint = f"{args.kind}s/{quote(args.id, safe='')}"
        else:
            endpoint = f"{args.kind}s/{quote(args.id, safe='')}/archive"
            if args.kind == "file":
                if not args.path:
                    raise ValueError("get file requires a relative file path")
                endpoint = f"nodes/{quote(args.id, safe='')}/files/{quote(args.path, safe='/')}"
            elif args.kind == "source":
                endpoint = f"sources/{quote(args.id, safe='')}/file"
        with httpx.Client(timeout=60, trust_env=False) as client:
            response = client.request(
                method,
                f"{args.url.rstrip('/')}/projects/{quote(args.project, safe='')}/{endpoint}",
                headers=headers,
                content=content,
            )
        if response.is_error:
            raise ValueError(f"HTTP {response.status_code}: {response.text}")
        if args.command == "get":
            if args.kind in ("file", "source"):
                save_file(
                    args.out,
                    response.content,
                    response.headers.get("X-Sharey-Executable") == "true",
                )
            else:
                save_archive(
                    args.out,
                    response.content,
                    int(response.headers.get("X-Sharey-Archive-Unpacked-Bytes", 16 * 1024 * 1024)),
                    int(response.headers.get("X-Sharey-Archive-Entries", 1000)),
                )
            print(json.dumps({"out": str(args.out), "id": args.id}))
        else:
            print(json.dumps(response.json(), ensure_ascii=False))
        return 0
    except (OSError, ValueError, httpx.HTTPError, ShareyError) as error:
        print(f"sharey: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
