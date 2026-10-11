import hashlib
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sharey.archives import relative_path

ObjectID = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class Publication(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1]
    title: str = Field(min_length=1, max_length=240)
    summary: str = Field(max_length=2000)
    contributor: str = Field(min_length=1, max_length=100)


class GitOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    commit: ObjectID
    path: str
    state: Literal["clean", "modified", "untracked"]


class FileProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    path: str
    source_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git: GitOrigin | None = None


class Node(Publication):
    parents: list[ObjectID] = Field(default_factory=list)
    sources: list[ObjectID] = Field(default_factory=list)
    skills: list[ObjectID] = Field(default_factory=list)
    provenance: list[FileProvenance] = Field(default_factory=list)


class Source(Publication):
    filename: str


class SelectedFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    source: str = Field(min_length=1)
    path: str = Field(min_length=1)


class NodeManifest(Node):
    memory: str = Field(min_length=1)
    files: list[SelectedFile]


class Limits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    max_upload_bytes: int = Field(default=16 * 1024 * 1024, gt=0)
    max_unpacked_bytes: int = Field(default=16 * 1024 * 1024, gt=0)
    max_entries: int = Field(default=1000, gt=0)


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    goal: str = Field(min_length=1)
    token: str = Field(min_length=1, pattern=r"^[\x21-\x7e]+$")


class ServerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    projects: dict[
        Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")], ProjectConfig
    ] = Field(min_length=1)
    limits: Limits = Field(default_factory=Limits)

    @model_validator(mode="after")
    def distinct_project_directories(self) -> Self:
        names = [name.casefold() for name in self.projects]
        if len(names) != len(set(names)):
            raise ValueError("Project identifiers must have distinct case-insensitive spellings")
        return self


def validate_publication(kind: str, metadata: dict, files: dict, directories: list[str]) -> dict:
    models: dict[str, type[Publication]] = {"nodes": Node, "sources": Source, "skills": Publication}
    model = models[kind].model_validate(metadata)
    paths = set(files)
    if kind == "nodes":
        if "memory.md" not in paths or any(
            path != "memory.md" and not path.startswith("files/") for path in paths
        ):
            raise ValueError("Node requires memory.md and explicitly selected files")
        files["memory.md"][0].decode("utf-8")
        if any(path != "files" and not path.startswith("files/") for path in directories):
            raise ValueError("Invalid node directory")
        assert isinstance(model, Node)
        for entry in model.provenance:
            path = "files/" + relative_path(entry.path)
            if path not in files or hashlib.sha256(files[path][0]).hexdigest() != entry.sha256:
                raise ValueError("Provenance digest does not match the published snapshot")
    elif kind == "skills":
        if "skill/SKILL.md" not in paths or any(not path.startswith("skill/") for path in paths):
            raise ValueError("Complete Skill requires a root SKILL.md")
        files["skill/SKILL.md"][0].decode("utf-8")
        if any(path != "skill" and not path.startswith("skill/") for path in directories):
            raise ValueError("Invalid Skill directory")
    else:
        assert isinstance(model, Source)
        filename = relative_path(model.filename)
        if (
            "/" in filename
            or paths != {"files/" + filename}
            or any(path != "files" for path in directories)
        ):
            raise ValueError("Source requires exactly its named file")
    return model.model_dump()
