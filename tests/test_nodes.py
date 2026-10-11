import io
import json
import zipfile

from conftest import AUTH


def bundle(metadata, files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
        for path, content in files.items():
            info = zipfile.ZipInfo(path)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()


def node_bundle(title="Baseline", parents=None, sources=None, skills=None, files=None):
    return bundle(
        {
            "schema_version": 1,
            "title": title,
            "summary": "Two observations; more trials needed.",
            "contributor": "Alice",
            "parents": parents or [],
            "sources": sources or [],
            "skills": skills or [],
        },
        {
            "memory.md": b"# Goal\nCompare measurements.\n",
            **(files or {"files/results.csv": b"x,y\n1,2\n"}),
        },
    )


def publish(api, content=None, key="root", kind="nodes", token="demo-secret", project="demo"):
    return api.post(
        f"/projects/{project}/{kind}",
        content=content or node_bundle(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip",
            "Idempotency-Key": key,
        },
    )


def test_publish_current_bytes_and_read_immutable_node(api):
    response = publish(api)
    assert response.status_code == 201, response.text
    node = response.json()
    assert len(node["id"]) == 40
    assert node["parents"] == []
    loaded = api.get(f"/projects/demo/nodes/{node['id']}", headers=AUTH)
    assert loaded.status_code == 200
    assert loaded.json()["title"] == "Baseline"
    assert loaded.json()["memory"] == "# Goal\nCompare measurements.\n"
    assert loaded.json()["files"] == [{"path": "results.csv", "size": 8, "executable": False}]
    raw = api.get(f"/projects/demo/nodes/{node['id']}/files/results.csv", headers=AUTH)
    assert raw.content == b"x,y\n1,2\n"
    assert api.get("/projects/demo/nodes", headers=AUTH).json()[0]["id"] == node["id"]
    assert api.get("/projects/demo/overview", headers=AUTH).json()["nodes"][0]["id"] == node["id"]
