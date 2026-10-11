import concurrent.futures

import httpx
import pytest
from conftest import AUTH
from test_nodes import node_bundle, publish


def test_retry_returns_original_publication_and_changed_content_conflicts(api):
    first = publish(api, node_bundle(), key="stable")
    assert first.status_code == 201
    retry = publish(api, node_bundle(), key="stable")
    assert retry.status_code == 201
    assert retry.json() == first.json()
    changed = publish(api, node_bundle("Different"), key="stable")
    assert changed.status_code == 409
    assert api.get("/projects/demo/nodes", headers=AUTH).json() == [first.json()]


def test_simultaneous_retries_and_distinct_branches_survive_real_http(service):
    base = service.url + "/projects/demo"

    def post(content, key):
        return httpx.post(
            base + "/nodes",
            content=content,
            headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": key},
            timeout=20,
        )

    root = post(node_bundle(), "root").json()["id"]
    same = node_bundle("Concurrent", parents=[root])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        retries = list(pool.map(lambda _: post(same, "same"), range(8)))
    assert all(response.status_code == 201 for response in retries), [
        (r.status_code, r.text) for r in retries
    ]
    assert len({response.json()["id"] for response in retries}) == 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        branches = list(
            pool.map(
                lambda i: post(node_bundle(f"Branch {i}", parents=[root]), f"branch-{i}"), range(6)
            )
        )
    assert all(response.status_code == 201 for response in branches)
    view = httpx.get(base + "/overview", headers=AUTH).json()
    assert len(view["nodes"]) == 8
    assert {node["id"] for node in view["nodes"]} == {
        root,
        retries[0].json()["id"],
        *(r.json()["id"] for r in branches),
    }
    assert all(node["parents"] == [root] for node in view["nodes"] if node["id"] != root)


def test_real_process_restart_keeps_assets_dag_bytes_and_retry_identity(service):
    from test_nodes import bundle

    def post(kind, content, key):
        return httpx.post(
            service.url + f"/projects/demo/{kind}",
            content=content,
            headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": key},
            timeout=20,
        )

    source_payload = bundle(
        {
            "schema_version": 1,
            "title": "Reference",
            "summary": "",
            "contributor": "Alice",
            "filename": "ref.bin",
        },
        {"files/ref.bin": b"\x00reference\xff"},
    )
    skill_payload = bundle(
        {"schema_version": 1, "title": "Method", "summary": "", "contributor": "Alice"},
        {"skill/SKILL.md": b"# Method", "skill/assets/value": b"7"},
    )
    source = post("sources", source_payload, "source").json()
    skill = post("skills", skill_payload, "skill").json()
    root_payload = node_bundle("Root", sources=[source["id"]], skills=[skill["id"]])
    root = post("nodes", root_payload, "root").json()
    child_payload = node_bundle("Child", parents=[root["id"]])
    child = post("nodes", child_payload, "child").json()
    before = httpx.get(service.url + "/projects/demo/overview", headers=AUTH).json()
    service.stop(kill=True)
    service.start()
    assert httpx.get(service.url + "/projects/demo/overview", headers=AUTH).json() == before
    for kind, payload, key, original in [
        ("nodes", root_payload, "root", root),
        ("nodes", child_payload, "child", child),
        ("sources", source_payload, "source", source),
        ("skills", skill_payload, "skill", skill),
    ]:
        response = post(kind, payload, key)
        assert response.status_code == 201
        assert response.json() == original
    assert (
        httpx.get(service.url + f"/projects/demo/sources/{source['id']}/file", headers=AUTH).content
        == b"\x00reference\xff"
    )
    assert (
        httpx.get(
            service.url + f"/projects/demo/nodes/{child['id']}/files/results.csv", headers=AUTH
        ).content
        == b"x,y\n1,2\n"
    )


@pytest.mark.parametrize(
    "stage,visible_before_kill",
    [
        ("during-objects", False),
        ("before-ref", False),
        ("after-ref", True),
    ],
)
def test_process_interruption_never_exposes_half_publication_and_retry_recovers(
    service, tmp_path, stage, visible_before_kill
):
    import json
    import time

    root = httpx.post(
        service.url + "/projects/demo/nodes",
        content=node_bundle(),
        headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": "root"},
    ).json()["id"]
    service.stop()
    markers = tmp_path / "faults"
    service.start(
        {
            "SHAREY_TEST_FAULT_DIR": str(markers),
            "SHAREY_TEST_PAUSE_STAGE": stage,
            "SHAREY_TEST_PAUSE_KEY": "interrupted",
        }
    )
    payload = node_bundle("Interrupted", parents=[root])

    def interrupted_request():
        try:
            return httpx.post(
                service.url + "/projects/demo/nodes",
                content=payload,
                headers={
                    **AUTH,
                    "Content-Type": "application/zip",
                    "Idempotency-Key": "interrupted",
                },
                timeout=15,
            )
        except httpx.HTTPError:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(interrupted_request)
        marker = markers / f"{stage}.json"
        deadline = time.monotonic() + 4
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        try:
            assert marker.exists(), "Controlled publication stage was not reached"
            marked = json.loads(marker.read_text())
            assert marked["stage"] == stage
            before = httpx.get(
                service.url + "/projects/demo/overview", headers=AUTH, timeout=5
            ).json()
            assert len(before["nodes"]) == (2 if visible_before_kill else 1)
            for node in before["nodes"]:
                loaded = httpx.get(
                    service.url + f"/projects/demo/nodes/{node['id']}", headers=AUTH
                ).json()
                assert loaded["memory"] == "# Goal\nCompare measurements.\n"
                assert (
                    httpx.get(
                        service.url + f"/projects/demo/nodes/{node['id']}/files/results.csv",
                        headers=AUTH,
                    ).content
                    == b"x,y\n1,2\n"
                )
        finally:
            service.stop(kill=True)
        pending.result(timeout=10)
    service.start()
    after = httpx.get(service.url + "/projects/demo/overview", headers=AUTH).json()
    assert len(after["nodes"]) == (2 if visible_before_kill else 1)
    response = httpx.post(
        service.url + "/projects/demo/nodes",
        content=payload,
        headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": "interrupted"},
    )
    assert response.status_code == 201, response.text
    if visible_before_kill:
        assert response.json()["id"] == next(n["id"] for n in after["nodes"] if n["id"] != root)
    assert response.json()["parents"] == [root]
    assert len(httpx.get(service.url + "/projects/demo/nodes", headers=AUTH).json()) == 2
    assert httpx.get(service.url + f"/projects/demo/nodes/{root}", headers=AUTH).status_code == 200


def test_startup_recovers_stale_git_ref_locks_after_process_exit(service):
    import hashlib

    key = "after-stale-lock"
    ref = (
        service.data
        / "demo.git/refs/sharey/nodes"
        / (hashlib.sha256(key.encode()).hexdigest() + ".lock")
    )
    service.stop(kill=True)
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_bytes(b"incomplete-ref-write")
    service.start()
    response = httpx.post(
        service.url + "/projects/demo/nodes",
        content=node_bundle(),
        headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": key},
    )
    assert response.status_code == 201, response.text
    assert not ref.exists()


def test_second_service_cannot_take_live_data_directory(service, tmp_path):
    import os
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sharey.cli",
            "serve",
            "--config",
            str(service.config),
            "--data-dir",
            str(service.data),
            "--port",
            "0",
        ],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode != 0
    assert "already in use" in completed.stderr
    assert httpx.get(service.url + "/projects/demo/overview", headers=AUTH).status_code == 200


def test_concurrent_different_content_on_same_key_has_one_winner(service):
    def post(i):
        return httpx.post(
            service.url + "/projects/demo/nodes",
            content=node_bundle(f"Candidate {i}"),
            headers={**AUTH, "Content-Type": "application/zip", "Idempotency-Key": "race"},
            timeout=20,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(post, range(5)))
    assert sorted(r.status_code for r in results) == [201, 409, 409, 409, 409]
    winner = next(r.json() for r in results if r.status_code == 201)
    assert httpx.get(service.url + "/projects/demo/nodes", headers=AUTH).json() == [winner]
