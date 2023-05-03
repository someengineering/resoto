import pytest

from resotocore.analytics import InMemoryEventSender, CoreEvent
from resotocore.config import ConfigHandler
from resotocore.db.system_data_db import SystemDataDb
from resotocore.user import UserManagement, UsersConfigId


@pytest.mark.asyncio
async def test_user_creation(
    config_handler: ConfigHandler,
    user_management: UserManagement,
    event_sender: InMemoryEventSender,
    system_data_db: SystemDataDb,
) -> None:
    await config_handler.delete_config(UsersConfigId)  # clean slate
    assert await user_management.has_users() is False
    user = await user_management.create_first_user("some company", "some name", "test@some.engineering", "bombproof")
    # make sure user is created
    assert user.fullname == "some name"
    assert user.roles == {"admin"}
    # an analytics event should have been sent
    assert [event for event in event_sender.events if event.kind == CoreEvent.FirstUserCreated]
    # the company is set in the system data db
    assert (await system_data_db.info())["company"] == "some company"
    # can not create a second user
    with pytest.raises(AssertionError):
        await user_management.create_first_user("some company", "some name", "test@some.engineering", "bombproof")
    # user login is possible
    assert await user_management.login("test@some.engineering", "bombproof") == user
    # wrong password is not accepted
    assert await user_management.login("test@some.engineering", "wrong password") is None
