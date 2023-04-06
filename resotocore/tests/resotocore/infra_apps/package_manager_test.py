from typing import cast, Awaitable
from resotocore.infra_apps.package_manager import PackageManager, AppManifestEntityDb, app_manifest_entity_db, FromGit
import pytest
from resotocore.ids import InfraAppName
from resotocore.db.async_arangodb import AsyncArangoDB
from arango.database import StandardDatabase
from types import SimpleNamespace
from resotocore.config import ConfigHandler
from asyncio import Future


@pytest.fixture
async def model_db(test_db: StandardDatabase) -> AppManifestEntityDb:
    async_db = AsyncArangoDB(test_db)
    entity_db = app_manifest_entity_db(async_db, "app_manifest_entity_db")
    await entity_db.create_update_schema()
    await entity_db.wipe()
    return entity_db


def async_none() -> Awaitable[None]:
    future: Future[None] = Future()
    future.set_result(None)
    return future


config_handler = cast(
    ConfigHandler,
    SimpleNamespace(
        put_config=lambda config_entity, validate: async_none(),
        delete_config=lambda config_id: async_none(),
        update_configs_model=lambda models: async_none(),
        put_config_validation=lambda config_validation: async_none(),
    ),
)


@pytest.mark.asyncio
async def test_install_delete(model_db: AppManifestEntityDb) -> None:
    name = InfraAppName("cleanup_untagged")
    repo_url = "https://github.com/someengineering/resoto-apps.git"
    package_manager = PackageManager(model_db, config_handler)
    manifest = await package_manager.install(name, FromGit(repo_url))
    assert manifest is not None
    assert manifest.name == name

    # check that it is installed
    installed_apps = [name async for name in package_manager.list()]
    assert installed_apps == [name]

    installed_app = await package_manager.info(name)
    assert installed_app is not None
    assert installed_app.name == name

    # check that it can be deleted
    await package_manager.delete(name)

    # check that it is not installed anymore
    installed_apps_after_deletion = [name async for name in package_manager.list()]
    assert installed_apps_after_deletion == []
