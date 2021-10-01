import json
from datetime import timedelta
from typing import AsyncGenerator

import pytest

from core.db.graphdb import ArangoGraphDB
from core.db.model import GraphUpdate
from core.dependencies import parse_args
from core.event_bus import EventBus, Message
from core.model.db_updater import merge_graph_process
from core.model.model import Kind
from core.model.typed_model import to_js
from tests.core.db.graphdb_test import create_graph

# noinspection PyUnresolvedReferences
from tests.core.db.graphdb_test import graph_db, foo_kinds, test_db

# noinspection PyUnresolvedReferences
from tests.core.event_bus_test import event_bus, all_events


@pytest.mark.asyncio
async def test_merge_process(
    event_bus: EventBus,
    graph_db: ArangoGraphDB,
    foo_kinds: list[Kind],
    all_events: list[Message],
) -> None:

    # wipe any existing data
    await graph_db.wipe()
    # store the model in db, so it can be loaded by the sub process
    graph_db.db.collection("model").insert_many([to_js(a) for a in foo_kinds])
    # define args to parse for the sub process
    args = parse_args(["--graphdb-username", "test", "--graphdb-password", "test", "--graphdb-database", "test"])
    # create sample graph data to insert
    graph = create_graph("test")

    async def iterator() -> AsyncGenerator[bytes, None]:
        for node in graph.nodes():
            yield bytes(json.dumps(graph.nodes[node]), "utf-8")
        for from_node, to_node in graph.edges():
            yield bytes(json.dumps({"from": from_node, "to": to_node}), "utf-8")

    result = await merge_graph_process(event_bus, args, iterator(), "ns", timedelta(seconds=30), None)
    assert result == GraphUpdate(112, 1, 0, 112, 0, 0)
