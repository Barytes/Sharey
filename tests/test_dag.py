import subprocess

from conftest import AUTH
from test_nodes import node_bundle, publish


def test_branches_and_merge_use_exact_git_parents_and_shared_navigation(api, tmp_path):
    root = publish(api, node_bundle("Root"), key="root").json()["id"]
    left = publish(api, node_bundle("Left", parents=[root]), key="left").json()["id"]
    right = publish(api, node_bundle("Right", parents=[root]), key="right").json()["id"]
    merged = publish(api, node_bundle("Merge", parents=[left, right]), key="merge").json()["id"]
    expected = {root: [], left: [root], right: [root], merged: [left, right]}
    overview = api.get("/projects/demo/overview", headers=AUTH).json()
    assert {node["id"]: node["parents"] for node in overview["nodes"]} == expected
    for oid, parents in expected.items():
        actual = api.get(f"/projects/demo/nodes/{oid}", headers=AUTH).json()
        assert actual["parents"] == parents
        result = subprocess.run(
            [
                "git",
                "--git-dir",
                str(tmp_path / "data/demo.git"),
                "rev-list",
                "--parents",
                "-n",
                "1",
                oid,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.split() == [oid, *parents]
    index = api.get("/projects/demo/index", headers=AUTH)
    assert index.status_code == 200
    assert "Compare measurements" in index.text
    for oid in expected:
        assert oid in index.text
    assert f"{left}, {right}" in index.text


def test_invalid_references_never_publish_or_change_existing_navigation(api):
    from test_nodes import bundle

    source = publish(
        api,
        bundle(
            {
                "schema_version": 1,
                "title": "Reference",
                "summary": "",
                "contributor": "Alice",
                "filename": "ref.txt",
            },
            {"files/ref.txt": b"reference"},
        ),
        key="src",
        kind="sources",
    ).json()["id"]
    skill = publish(
        api,
        bundle(
            {"schema_version": 1, "title": "Method", "summary": "", "contributor": "Alice"},
            {"skill/SKILL.md": b"# Method"},
        ),
        key="skill",
        kind="skills",
    ).json()["id"]
    root = publish(api, node_bundle(sources=[source], skills=[skill])).json()["id"]
    other = publish(
        api, node_bundle("Other project"), key="other-root", project="other", token="other-secret"
    ).json()["id"]
    baseline = api.get("/projects/demo/overview", headers=AUTH).json()
    cases = [
        {"parents": ["f" * 40]},
        {"parents": [other]},
        {"parents": [source]},
        {"parents": [root, root]},
        {"sources": ["e" * 40]},
        {"sources": [skill]},
        {"skills": ["d" * 40]},
        {"skills": [source]},
    ]
    for number, references in enumerate(cases):
        response = publish(api, node_bundle("Rejected", **references), key=f"bad-{number}")
        assert response.status_code == 422, response.text
        assert api.get("/projects/demo/overview", headers=AUTH).json() == baseline
    valid = api.get(f"/projects/demo/nodes/{root}", headers=AUTH).json()
    assert valid["sources"] == [source]
    assert valid["skills"] == [skill]
    assert api.get(f"/projects/demo/nodes/{other}", headers=AUTH).status_code == 404
    assert api.get(f"/projects/demo/nodes/{source}", headers=AUTH).status_code == 404
