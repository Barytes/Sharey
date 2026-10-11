from fastapi.testclient import TestClient

from sharey.server import create_app


def test_member_can_read_project_goal_and_empty_navigation(tmp_path):
    app = create_app(
        tmp_path, {"projects": {"demo": {"goal": "Compare measurements", "token": "demo-secret"}}}
    )
    with TestClient(app) as client:
        response = client.get(
            "/projects/demo/overview", headers={"Authorization": "Bearer demo-secret"}
        )
    assert response.status_code == 200
    assert response.json() == {
        "project": "demo",
        "goal": "Compare measurements",
        "nodes": [],
        "sources": [],
        "skills": [],
    }


def test_project_routes_reject_missing_wrong_and_other_project_credentials(tmp_path):
    app = create_app(
        tmp_path,
        {
            "projects": {
                "demo": {"goal": "private-goal", "token": "demo-secret"},
                "other": {"goal": "other-private-goal", "token": "other-secret"},
            }
        },
    )
    with TestClient(app) as client:
        for project in ("demo", "missing"):
            for token in (None, "wrong", "other-secret"):
                headers = {} if token is None else {"Authorization": f"Bearer {token}"}
                response = client.get(f"/projects/{project}/overview", headers=headers)
                assert response.status_code == 401
                assert "private-goal" not in response.text
                assert "secret" not in response.text


def test_every_object_read_and_publish_requires_matching_project_credential(api):
    from test_nodes import node_bundle

    for token in ("", "wrong", "other-secret"):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        for endpoint in (
            "overview",
            "index",
            "nodes",
            "sources",
            "skills",
            "nodes/" + "f" * 40,
            "nodes/" + "f" * 40 + "/archive",
            "nodes/" + "f" * 40 + "/files/a",
            "sources/" + "f" * 40,
            "sources/" + "f" * 40 + "/file",
            "skills/" + "f" * 40,
            "skills/" + "f" * 40 + "/archive",
        ):
            response = api.get("/projects/demo/" + endpoint, headers=headers)
            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid project credential"}
        for kind in ("nodes", "sources", "skills"):
            response = api.post(
                "/projects/demo/" + kind,
                content=node_bundle(),
                headers={**headers, "Content-Type": "application/zip", "Idempotency-Key": "denied"},
            )
            assert response.status_code == 401
    assert (
        api.get("/projects/demo/nodes", headers={"Authorization": "Bearer demo-secret"}).json()
        == []
    )
