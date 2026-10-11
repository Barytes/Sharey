import io
import json
import re
import secrets
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from sharey.archives import decode
from sharey.errors import ShareyError
from sharey.lease import storage_lease
from sharey.models import ServerConfig, validate_publication
from sharey.storage import GitStore


def create_app(data_dir: Path, config: dict) -> FastAPI:
    try:
        settings = ServerConfig.model_validate(config)
    except ValueError as error:
        raise ValueError("Invalid server configuration") from error
    config = settings.model_dump()
    store: GitStore

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal store
        with storage_lease(data_dir, config["projects"]):
            store = GitStore(data_dir, config["projects"])
            yield

    app = FastAPI(title="Sharey", lifespan=lifespan)
    limits = settings.limits

    @app.exception_handler(ShareyError)
    async def domain_error(request: Request, error: ShareyError):
        return JSONResponse({"detail": error.message}, status_code=error.status)

    def authorize(project: str, authorization: str = Header(default="")) -> None:
        expected = config["projects"].get(project, {}).get("token", "")
        if not expected or not secrets.compare_digest(
            authorization.encode(), f"Bearer {expected}".encode()
        ):
            raise HTTPException(
                401, "Invalid project credential", headers={"WWW-Authenticate": "Bearer"}
            )

    router = APIRouter(prefix="/projects/{project}", dependencies=[Depends(authorize)])

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @router.get("/overview")
    def overview(project: str):
        return {
            "project": project,
            "goal": config["projects"][project]["goal"],
            "nodes": store.listing(project, "nodes"),
            "sources": store.listing(project, "sources"),
            "skills": store.listing(project, "skills"),
        }

    @router.get("/index")
    def index(project: str):
        view = overview(project)
        lines = [f"# {project}", "", view["goal"], ""]
        for kind in ("nodes", "sources", "skills"):
            lines.extend([f"## {kind}", ""])
            for item in view[kind]:
                parents = ", ".join(item["parents"]) or "root"
                lines.extend(
                    [
                        (
                            f"- [{item['title']}](/projects/{project}/{kind}/{item['id']}) "
                            f"({item['id']})"
                        ),
                        f"  {item['summary']} | {item['contributor']} | {item['created_at']}",
                        f"  parents: {parents}",
                    ]
                )
            lines.append("")
        return Response("\n".join(lines), media_type="text/markdown")

    @router.get("/{kind}")
    def list_objects(project: str, kind: str):
        if kind not in ("nodes", "sources", "skills"):
            raise HTTPException(404, "Unknown object type")
        return store.listing(project, kind)

    @router.post("/{kind}", status_code=201)
    async def publish_object(
        project: str,
        kind: str,
        request: Request,
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        if kind not in ("nodes", "sources", "skills"):
            raise HTTPException(404, "Unknown object type")
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", idempotency_key):
            raise ShareyError(
                422,
                "Idempotency-Key must be 1-128 ASCII letters, digits, dots, underscores or hyphens",
            )
        if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/zip":
            raise ShareyError(415, "Expected application/zip")
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > limits.max_upload_bytes:
                raise ShareyError(413, "Upload byte limit exceeded")
            body.extend(chunk)
        try:
            files, directories = await run_in_threadpool(
                decode, bytes(body), limits.max_unpacked_bytes, limits.max_entries
            )
            metadata = json.loads(files.pop("metadata.json")[0])
            metadata = validate_publication(kind, metadata, files, directories)
        except (ValueError, KeyError) as error:
            raise ShareyError(422, "Invalid publication archive") from error
        return await run_in_threadpool(
            store.publish, project, kind, idempotency_key, metadata, files, directories
        )

    @router.get("/skills/{oid}")
    def show_skill(project: str, oid: str):
        return store.describe(project, "skills", oid)

    def archive_response(project: str, kind: str, oid: str) -> Response:
        content = store.archive(project, kind, oid)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            headers = {
                "X-Sharey-Archive-Unpacked-Bytes": str(sum(entry.file_size for entry in entries)),
                "X-Sharey-Archive-Entries": str(len(entries)),
            }
        return Response(content, media_type="application/zip", headers=headers)

    @router.get("/skills/{oid}/archive")
    def get_skill_archive(project: str, oid: str):
        return archive_response(project, "skills", oid)

    @router.get("/sources/{oid}")
    def show_source(project: str, oid: str):
        return store.describe(project, "sources", oid)

    @router.get("/sources/{oid}/file")
    def get_source(project: str, oid: str):
        source = store.describe(project, "sources", oid)
        return Response(
            store.blob(project, oid, "files/" + source["filename"]),
            media_type="application/octet-stream",
            headers={"X-Sharey-Executable": str(source["files"][0]["executable"]).lower()},
        )

    @router.get("/nodes/{oid}")
    def show_node(project: str, oid: str):
        result = store.describe(project, "nodes", oid)
        result["memory"] = store.blob(project, oid, "memory.md").decode("utf-8")
        return result

    @router.get("/nodes/{oid}/files/{path:path}")
    def get_file(project: str, oid: str, path: str):
        store.require(project, "nodes", oid)
        content = store.blob(project, oid, "files/" + path)
        executable = store.entries(project, oid)["files/" + path][0] == "100755"
        return Response(
            content,
            media_type="application/octet-stream",
            headers={"X-Sharey-Executable": str(executable).lower()},
        )

    @router.get("/nodes/{oid}/archive")
    def get_node_archive(project: str, oid: str):
        return archive_response(project, "nodes", oid)

    app.include_router(router)
    return app
