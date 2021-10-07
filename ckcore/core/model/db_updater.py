import asyncio
import json
import logging
import sys
from abc import ABC
from argparse import Namespace
from asyncio import Task
from contextlib import suppress
from dataclasses import dataclass
from datetime import timedelta
from multiprocessing import Process, Queue
from queue import Empty
from typing import Optional, Union, AsyncGenerator, Any, Generator, List, cast

from aiostream import stream
from aiostream.core import Stream

from core.async_extensions import run_async
from core.db.db_access import DbAccess
from core.db.graphdb import GraphDB
from core.db.model import GraphUpdate
from core.dependencies import db_access, setup_process, reset_process_start_method
from core.error import ImportAborted
from core.event_bus import EventBus, Message
from core.model.graph_access import GraphBuilder
from core.model.model import Model
from core.types import Json
from core.util import utc, uuid_str

log = logging.getLogger(__name__)


class ProcessAction(ABC):
    """
    Base class to exchange commands between processes.
    Important: all messages must be serializable in order to get pickled/unpickled.
    """


@dataclass
class ReadElement(ProcessAction):
    """
    Read an incoming element:
    - either a line of text or
    - a complete json element
    Parent -> Child: for every incoming data line.
    """

    elements: List[Union[bytes, Json]]

    def jsons(self) -> Generator[Json, Any, None]:
        return (e if isinstance(e, dict) else json.loads(e) for e in self.elements)


@dataclass
class MergeGraph(ProcessAction):
    """
    Merge the graph that has been read so far.
    Parent -> Child: once EOF of the incoming graph is reached.
    """

    graph: str
    change_id: str
    is_batch: bool = False


@dataclass
class EmitMessage(ProcessAction):
    """
    Emit this message to the event bus.
    Child -> Parent: to have the event from the child process propagated to the parent process.
    """

    event: Message


class PoisonPill(ProcessAction):
    """
    Sentence the process to die.
    Parent -> Child: when the update process is interrupted.
    """


@dataclass
class Result(ProcessAction):
    result: Union[GraphUpdate, str]

    def get_value(self) -> GraphUpdate:
        if isinstance(self.result, str):
            raise ImportAborted(self.result)
        else:
            return self.result


BatchSize = 100000


class DbUpdaterProcess(Process):
    """
    This update class implements Process and is supposed to run as separate process.
    Note: default starting method is supposed to be "spawn".

    This process has 2 queues to read input from and write output to.
    All elements in either queues are of type ProcessAction.

    The parent process should stream the raw parts of graph to this process via ReadElement objects.
    Once the MergeGraph action is received, the graph gets imported.
    From here the parent expects result messages from the child.
    All events happen in the child are forwarded to the parent via EmitEvent.
    Once the graph update is done, a result is send.
    The result is either an exception in case of failure or a graph update in success case.
    """

    def __init__(self, read_queue: Queue, write_queue: Queue, args: Namespace) -> None:  # type: ignore
        super().__init__(name="merge_update")
        self.read_queue = read_queue
        self.write_queue = write_queue
        self.args = args

    def next_action(self) -> ProcessAction:
        return self.read_queue.get(True, 30)  # type: ignore

    def forward_events(self, bus: EventBus) -> Task:
        async def forward_events_forever() -> None:
            with bus.subscribe("event_forwarder") as events:
                while True:
                    event = await events.get()
                    self.write_queue.put(EmitMessage(event))

        return asyncio.create_task(forward_events_forever())

    async def merge_graph(self, db: DbAccess) -> GraphUpdate:  # type: ignore
        model = Model.from_kinds([kind async for kind in db.model_db.all()])
        builder = GraphBuilder(model)
        nxt = self.next_action()
        while isinstance(nxt, ReadElement):
            for element in nxt.jsons():
                builder.add_from_json(element)
            log.debug(f"Read {int(BatchSize / 1000)}K elements in process")
            nxt = self.next_action()
        if isinstance(nxt, PoisonPill):
            log.debug("Got poison pill - going to die.")
            sys.exit(0)
        elif isinstance(nxt, MergeGraph):
            log.debug("Graph read into memory")
            builder.check_complete()
            graphdb = db.get_graph_db(nxt.graph)
            _, result = await graphdb.merge_graph(builder.graph, model, nxt.change_id, nxt.is_batch)
            return result

    async def setup_and_merge(self) -> GraphUpdate:
        bus = EventBus()
        db = db_access(self.args, bus)
        task = self.forward_events(bus)
        result = await self.merge_graph(db)
        await asyncio.sleep(0.1)  # yield current process to drain event bus
        task.cancel()
        return result

    def run(self) -> None:
        try:
            # Entrypoint of the new service
            setup_process(self.args, f"merge_update_{self.pid}")
            log.info(f"Import process started: {self.pid}")
            result = asyncio.run(self.setup_and_merge())
            self.write_queue.put(Result(result))
            log.info(f"Update process done: {self.pid} Exit.")
            sys.exit(0)
        except Exception as ex:
            # not all exceptions can be pickled. Use string representation.
            self.write_queue.put(Result(repr(ex)))
            log.info("Update process interrupted. Preemptive Exit.")
            sys.exit(1)


async def merge_graph_process(
    db: GraphDB,
    bus: EventBus,
    args: Namespace,
    content: AsyncGenerator[Union[bytes, Json], None],
    max_wait: timedelta,
    maybe_batch: Optional[str],
) -> GraphUpdate:
    change_id = maybe_batch if maybe_batch else uuid_str()
    write = Queue()  # type: ignore
    read = Queue()  # type: ignore
    updater = DbUpdaterProcess(write, read, args)  # the process reads from our write queue and vice versa
    stale = timedelta(seconds=5).total_seconds()  # consider dead communication after this amount of time
    deadline = utc() + max_wait
    dead_adjusted = False

    async def send_to_child(pa: ProcessAction) -> bool:
        alive = updater.is_alive()
        if alive:
            await run_async(write.put, pa, True, stale)
        return alive

    def read_results() -> Task:
        async def read_forever() -> GraphUpdate:
            nonlocal deadline
            nonlocal dead_adjusted
            while utc() < deadline:
                # After exit of updater: adjust the deadline once
                if not updater.is_alive() and not dead_adjusted:
                    log.debug("Import process done or dead. Adjust deadline.")
                    deadline = utc() + timedelta(seconds=30)
                    dead_adjusted = True
                try:
                    action = await run_async(read.get, True, stale)
                    if isinstance(action, EmitMessage):
                        await bus.emit(action.event)
                    elif isinstance(action, Result):
                        return action.get_value()
                except Empty:
                    # empty is fine
                    pass
            raise ImportAborted(f"Import process died. (ExitCode: {updater.exitcode})")

        return asyncio.create_task(read_forever())

    task: Optional[Task] = None
    result: Optional[GraphUpdate] = None
    try:
        reset_process_start_method()  # other libraries might have tampered the value in the mean time
        updater.start()
        task = read_results()  # concurrently read result queue
        chunked: Stream = stream.chunks(content, BatchSize)
        async with chunked.stream() as streamer:  # pylint: disable=no-member
            async for lines in streamer:
                if not await send_to_child(ReadElement(lines)):
                    # in case the child is dead, we should stop
                    break
        await send_to_child(MergeGraph(db.name, change_id, maybe_batch is not None))
        result = cast(GraphUpdate, await task)  # wait for final result
        return result
    finally:
        if task is not None and not task.done():
            task.cancel()
        if not result:
            # make sure the change is aborted in case of transaction
            log.info(f"Abort update manually: {change_id}")
            await db.abort_update(change_id)
        await send_to_child(PoisonPill())
        await run_async(updater.join, stale)
        if updater.is_alive():
            log.warning(f"Process is still alive after poison pill. Terminate process {updater.pid}")
            with suppress(Exception):
                updater.terminate()
            await asyncio.sleep(3)
        if updater.is_alive():
            log.warning(f"Process is still alive after terminate. Kill process {updater.pid}")
            with suppress(Exception):
                updater.kill()
            await asyncio.sleep(3)
        if not updater.is_alive():
            with suppress(Exception):
                updater.close()
