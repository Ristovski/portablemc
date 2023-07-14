"""Definition of tasks for installing and running Fabric/Quilt mod loader.
"""

from .vanilla import MetadataRoot, MetadataTask, VersionRepository, Version, \
    VersionRepositories
from .task import Task, State, Watcher, Sequence
from .http import http_request

from typing import Optional, Any


class FabricApi:
    """This class is internally used to defined two constant for both official Fabric
    backend API and Quilt API which have the same endpoints. So we use the same logic
    for both mod loaders.
    """

    def __init__(self, name: str, api_url: str) -> None:
        self.name = name
        self.api_url = api_url
    
    def request_fabric_meta(self, method: str) -> Any:
        """Generic HTTP request to the fabric's REST API.
        """
        return http_request("GET", f"{self.api_url}{method}", accept="application/json").json()

    def request_fabric_loader_version(self, vanilla_version: str) -> str:
        return self.request_fabric_meta(f"versions/loader/{vanilla_version}")[0].get("loader", {}).get("version")

    def request_version_loader_profile(self, vanilla_version: str, loader_version: str) -> dict:
        return self.request_fabric_meta(f"versions/loader/{vanilla_version}/{loader_version}/profile/json")


FABRIC_API = FabricApi("fabric", "https://meta.fabricmc.net/v2/")
QUILT_API = FabricApi("quilt", "https://meta.quiltmc.org/v3/")


class FabricRoot:
    """Represent the root fabric version to load. The task `FabricInitTask` will only
    trigger if such state is present.
    """

    def __init__(self, api: FabricApi, prefix: str, vanilla_version: str, loader_version: Optional[str]) -> None:
        self.api = api
        self.prefix = prefix
        self.vanilla_version = vanilla_version
        self.loader_version = loader_version

    @classmethod
    def with_fabric(cls, prefix: str, vanilla_version: str, loader_version: Optional[str]) -> "FabricRoot":
        """Construct a root for resolving a Fabric version.
        """
        return cls(FABRIC_API, prefix, vanilla_version, loader_version)

    @classmethod
    def with_quilt(cls, prefix: str, vanilla_version: str, loader_version: Optional[str]) -> "FabricRoot":
        """Construct a root for resolving a Quilt version.
        """
        return cls(QUILT_API, prefix, vanilla_version, loader_version)


class FabricInitTask(Task):
    """This task loads metadata for a fabric version.

    :in VersionRoot: The root version to load. If this version's id follow the following
    format `prefix:[<mc-version>[:<loader-version>]]`, then this task will trigger and
    prepare the fabric's metadata.
    """

    def execute(self, state: State, watcher: Watcher) -> None:

        root = state.get(FabricRoot)
        if root is None:
            return
        
        vanilla_version = root.vanilla_version
        loader_version = root.loader_version

        if loader_version is None:
            watcher.on_event(FabricResolveEvent(root.api, vanilla_version, None))
            loader_version = root.api.request_fabric_loader_version(vanilla_version)

        watcher.on_event(FabricResolveEvent(root.api, vanilla_version, loader_version))

        # Update the root version id to a valid one (without :).
        version_id = f"{root.prefix}-{vanilla_version}-{loader_version}"

        state.insert(MetadataRoot(version_id))
        state[VersionRepositories].insert(version_id, FabricRepository(root.api, version_id, vanilla_version, loader_version))


class FabricRepository(VersionRepository):
    """Internal class used as instance mapped to the fabric version.
    """

    def __init__(self, api: FabricApi, version_id: str, vanilla_version: str, loader_version: str) -> None:
        self.api = api
        self.version_id = version_id
        self.vanilla_version = vanilla_version
        self.loader_version = loader_version

    def validate_version_meta(self, version: Version) -> bool:
        assert version.id == self.version_id, "should not trigger for this version"
        return True
    
    def fetch_version_meta(self, version: Version) -> None:
        version.metadata = self.api.request_version_loader_profile(self.vanilla_version, self.loader_version)
        version.metadata["id"] = self.version_id
        version.write_metadata_file()


class FabricResolveEvent:
    __slots__ = "api", "vanilla_version", "loader_version"
    def __init__(self, api: FabricApi, vanilla_version: str, loader_version: Optional[str]) -> None:
        self.api = api
        self.vanilla_version = vanilla_version
        self.loader_version = loader_version


def add_fabric_tasks(seq: Sequence) -> None:
    """Add tasks to a sequence for installing and running a Fabric mod loader version.

    The fabric tasks will run if the `FabricRoot` state is present, in such case a 
    `MetadataRoot` will be created if version resolution succeed.

    :param seq: The sequence to alter and add tasks to.
    """
    seq.prepend_task(FabricInitTask(), before=MetadataTask)