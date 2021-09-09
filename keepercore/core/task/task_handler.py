from __future__ import annotations

import asyncio
import logging
import re
from asyncio import Task, CancelledError
from datetime import timedelta
from io import TextIOWrapper
from typing import List, Dict, Tuple, Optional, Any, Callable, Union, Sequence

import argparse
from aiostream import stream
from argparse import ArgumentParser, Namespace

from functools import reduce

from copy import copy

from core.cli.cli import CLI
from core.db.jobdb import JobDb
from core.db.runningtaskdb import RunningTaskData, RunningTaskDb
from core.error import ParseError, CLIParseError
from core.event_bus import EventBus, Event, Action, ActionDone, Message, ActionError
from core.task.job_handler import JobHandler
from core.task.model import Subscriber
from core.task.scheduler import Scheduler
from core.task.subscribers import SubscriptionHandler
from core.task.task_description import (
    Workflow,
    RunningTask,
    EventTrigger,
    TimeTrigger,
    TaskSurpassBehaviour,
    PerformAction,
    Step,
    TaskDescription,
    Job,
    ExecuteCommand,
    TaskCommand,
    SendMessage,
    ExecuteOnCLI,
    StepErrorBehaviour,
)
from core.util import first, Periodic, group_by, uuid_str, utc_str

log = logging.getLogger(__name__)


class TaskHandler(JobHandler):

    # region init

    @staticmethod
    def add_args(arg_parser: ArgumentParser) -> None:
        arg_parser.add_argument("--jobs", nargs="*", type=argparse.FileType("r"))

    def __init__(
        self,
        running_task_db: RunningTaskDb,
        job_db: JobDb,
        event_bus: EventBus,
        subscription_handler: SubscriptionHandler,
        scheduler: Scheduler,
        cli: CLI,
        config: Namespace,
    ):
        self.running_task_db = running_task_db
        self.job_db = job_db
        self.event_bus = event_bus
        self.subscription_handler = subscription_handler
        self.scheduler = scheduler
        self.cli = cli
        self.config = config

        # Step1: define all workflows and jobs in code: later it will be persisted and read from database
        self.task_descriptions: Sequence[TaskDescription] = [*self.known_workflows(), *self.known_jobs()]
        self.tasks: Dict[str, RunningTask] = {}
        self.event_bus_watcher: Optional[Task[Any]] = None
        self.timeout_watcher = Periodic("task_timeout_watcher", self.check_overdue_tasks, timedelta(seconds=10))
        self.registered_event_trigger: List[Tuple[EventTrigger, TaskDescription]] = []
        self.registered_event_trigger_by_message_type: Dict[str, List[Tuple[EventTrigger, TaskDescription]]] = {}

    # endregion

    # region startup and teardown

    async def update_trigger(self, desc: TaskDescription, register: bool = True) -> None:
        # safeguard: unregister all event trigger of this task
        for existing in (tup for tup in self.registered_event_trigger if desc.id == tup[1].id):
            self.registered_event_trigger.remove(existing)
        # safeguard: unregister all schedule trigger of this task
        for job in self.scheduler.list_jobs():
            if str(job.id).startswith(desc.id):
                job.remove()
        # add all triggers
        if register:
            for trigger in desc.triggers:
                if isinstance(trigger, EventTrigger):
                    self.registered_event_trigger.append((trigger, desc))
                if isinstance(trigger, TimeTrigger):
                    uid = f"{desc.id}_{trigger.cron_expression}"
                    name = f"Trigger for task {desc.id} on cron expression {trigger.cron_expression}"
                    self.scheduler.cron(uid, name, trigger.cron_expression, self.time_triggered, desc, trigger)
        # recompute the lookup table
        self.registered_event_trigger_by_message_type = group_by(
            lambda t: t[0].message_type, self.registered_event_trigger
        )

    # task descriptors can hold placeholders (e.g. @NOW@)
    # which should be replaced, when the task is started (or restarted).
    def evaluate_task_definition(self, descriptor: TaskDescription, **env: str) -> TaskDescription:
        def evaluate(step: Step) -> Step:
            if isinstance(step.action, ExecuteCommand):
                update = copy(step)
                update.action = ExecuteCommand(self.cli.replace_placeholder(step.action.command, **env))
                return update
            else:
                return step

        updated = copy(descriptor)
        updated.steps = [evaluate(step) for step in descriptor.steps]
        return updated

    async def start_task(self, descriptor: TaskDescription) -> None:
        existing = first(lambda x: x.descriptor.id == descriptor.id, self.tasks.values())
        if existing:
            if descriptor.on_surpass == TaskSurpassBehaviour.Skip:
                log.info(
                    f"Task {descriptor.name} has been triggered. Since the last job is not finished, "
                    f"the execution will be skipped, as defined by the task"
                )
                return None
            elif descriptor.on_surpass == TaskSurpassBehaviour.Replace:
                log.info(f"New task {descriptor.name} should replace existing run: {existing.id}.")
                existing.end()
                await self.store_running_task_state(existing)
            elif descriptor.on_surpass == TaskSurpassBehaviour.Parallel:
                log.info(f"New task {descriptor.name} will race with existing run {existing.id}.")
            else:
                raise AttributeError(f"Surpass behaviour not handled: {descriptor.on_surpass}")

        updated = self.evaluate_task_definition(descriptor)
        wi, commands = RunningTask.empty(updated, self.subscription_handler.subscribers_by_event)
        log.info(f"Start new task: {updated.name} with id {wi.id}")
        # store initial state in database
        await self.running_task_db.insert(wi)
        self.tasks[wi.id] = wi
        await self.execute_task_commands(wi, commands)

    async def start_interrupted_tasks(self) -> list[RunningTask]:
        descriptions = {w.id: w for w in self.task_descriptions}

        def reset_state(wi: RunningTask, data: RunningTaskData) -> RunningTask:
            # reset the received messages
            wi.received_messages = data.received_messages  # type: ignore
            # move the fsm into the last known state
            wi.machine.set_state(data.current_state_name)
            # import state of the current step
            wi.current_state.import_state(data.current_state_snapshot)
            # reset times
            wi.task_started_at = data.task_started_at
            wi.step_started_at = data.step_started_at
            # ignore all messages that would be emitted
            wi.move_to_next_state()
            return wi

        instances: list[RunningTask] = []
        async for data in self.running_task_db.all():
            descriptor = descriptions.get(data.task_descriptor_id)
            if descriptor:
                # we have captured the timestamp when the task has been started
                updated = self.evaluate_task_definition(descriptor, now=utc_str(data.task_started_at))
                instance = RunningTask(data.id, updated, self.subscription_handler.subscribers_by_event)
                instances.append(reset_state(instance, data))
            else:
                log.warning(f"No task description with this id found: {data.task_descriptor_id}. Remove instance data.")
                await self.running_task_db.delete(data.id)
        return instances

    async def __aenter__(self) -> TaskHandler:
        log.info("TaskHandler is starting up!")

        # load job descriptions from configuration files
        file_jobs = [await self.parse_job_file(file) for file in self.config.jobs] if self.config.jobs else []
        jobs: list[Job] = reduce(lambda r, l: r + l, file_jobs, [])

        # load job descriptions from database
        db_jobs = [job async for job in self.job_db.all()]
        self.task_descriptions = [*self.task_descriptions, *jobs, *db_jobs]

        # load and restore all tasks
        self.tasks = {wi.id: wi for wi in await self.start_interrupted_tasks()}
        # TODO: it might be necessary to restart current commands (e.g. cli commands)

        await self.timeout_watcher.start()

        for descriptor in self.task_descriptions:
            await self.update_trigger(descriptor)

        async def listen_to_event_bus() -> None:
            with self.event_bus.subscribe("task_handler") as messages:
                while True:
                    try:
                        message = await messages.get()
                        if isinstance(message, Event):
                            await self.handle_event(message)
                        elif isinstance(message, Action):
                            await self.handle_action(message)
                        elif isinstance(message, (ActionDone, ActionError)):
                            log.info(f"Ignore message via event bus: {message}")
                    except Exception as ex:
                        log.error(f"Could not handle event {message} - give up.", ex)

        self.event_bus_watcher = asyncio.create_task(listen_to_event_bus())
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        log.info("Tear down task handler")
        # deregister from all triggers
        for descriptor in self.task_descriptions:
            await self.update_trigger(descriptor, register=False)

        # stop timeout watcher
        await self.timeout_watcher.stop()

        # stop event listener
        if self.event_bus_watcher:
            self.event_bus_watcher.cancel()
            try:
                await self.event_bus_watcher
            except CancelledError:
                log.info("task has been cancelled")

        # wait for all running commands to complete
        for task in list(self.tasks.values()):
            if task.update_task:
                await task.update_task
                del self.tasks[task.id]

    # endregion

    # region job handler

    async def list_jobs(self) -> list[Job]:
        return [job for job in self.task_descriptions if isinstance(job, Job)]

    async def add_job(self, job: Job) -> None:
        descriptions = list(self.task_descriptions)
        existing = first(lambda td: td.id == job.id, descriptions)
        if existing:
            if not existing.mutable:
                raise AttributeError(f"There is an existing job with this {job.id} which can not be deleted!")
            log.info(f"Job with id {job.id} already exists. Update this job.")
            descriptions.remove(existing)
        # store in database
        await self.job_db.update(job)
        descriptions.append(job)
        self.task_descriptions = descriptions
        await self.update_trigger(job)

    async def delete_running_task(self, task: RunningTask) -> None:
        task.descriptor_alive = False
        # remove tasks from list of running tasks
        self.tasks.pop(task.id, None)
        if task.update_task and not task.update_task.done():
            task.update_task.cancel("task description is deleted")

        # mark step as error
        task.end()
        # remove from database
        await self.running_task_db.delete(task.id)

    async def delete_job(self, job_id: str) -> Optional[Job]:
        job: Job = first(lambda td: td.id == job_id and isinstance(td, Job), self.task_descriptions)  # type: ignore
        if job:
            if not job.mutable:
                raise AttributeError(f"Can not delete job: {job.id} - it is defined in a system file!")
            # delete all running tasks of this job
            for task in list(filter(lambda x: x.descriptor.id == job.id, self.tasks.values())):
                log.info(f"Job: {job_id}: delete running task: {task.id}")
                await self.delete_running_task(task)
            await self.job_db.delete(job_id)
            descriptions = list(self.task_descriptions)
            descriptions.remove(job)
            self.task_descriptions = descriptions
            await self.update_trigger(job, register=False)
        return job

    # endregion

    # region maintain running tasks

    async def time_triggered(self, descriptor: TaskDescription, trigger: TimeTrigger) -> None:
        log.info(f"Task {descriptor.name} triggered by time: {trigger.cron_expression}")
        return await self.start_task(descriptor)

    async def handle_event(self, event: Event) -> None:
        # check if any running task want's to handle this event
        for wi in list(self.tasks.values()):
            handled, commands = wi.handle_event(event)
            if handled:
                await self.execute_task_commands(wi, commands, event)

        # check if this event triggers any new task
        for trigger, descriptor in self.registered_event_trigger_by_message_type.get(event.message_type, []):
            if event.message_type == trigger.message_type:
                comp = trigger.filter_data
                if {key: event.data.get(key) for key in comp} == comp if comp else True:
                    log.info(f"Event {event.message_type} triggers task: {descriptor.name}")
                    await self.start_task(descriptor)

    # noinspection PyMethodMayBeStatic
    async def handle_action(self, action: Action) -> None:
        log.info(f"Received action: {action.step_name}:{action.message_type} of {action.task_id}")

    async def handle_action_result(
        self, done: Union[ActionDone, ActionError], fn: Callable[[RunningTask], Sequence[TaskCommand]]
    ) -> None:
        wi = self.tasks.get(done.task_id)
        if wi:
            commands = fn(wi)
            return await self.execute_task_commands(wi, commands, done)
        else:
            log.warning(
                f"Received an ack for an unknown task={done.task_id} "
                f"event={done.message_type} from={done.subscriber_id}. Ignore."
            )

    async def handle_action_done(self, done: ActionDone) -> None:
        return await self.handle_action_result(done, lambda wi: wi.handle_done(done))

    async def handle_action_error(self, err: ActionError) -> None:
        log.info(f"Received error: {err.error} {err.step_name}:{err.message_type} of {err.task_id}")
        return await self.handle_action_result(err, lambda wi: wi.handle_error(err))

    async def execute_task_commands(
        self, wi: RunningTask, commands: Sequence[TaskCommand], origin_message: Optional[Message] = None
    ) -> None:
        async def execute_commands() -> None:
            # execute and collect all task commands
            results: dict[TaskCommand, Any] = {}
            for command in commands:
                if isinstance(command, SendMessage):
                    await self.event_bus.emit(command.message)
                    results[command] = None
                elif isinstance(command, ExecuteOnCLI):
                    # TODO: instead of executing it in process, we should do an http call here to a worker core.
                    result = await self.cli.execute_cli_command(command.command, stream.list, **command.env)
                    results[command] = result
                else:
                    raise AttributeError(f"Does not understand this command: {wi.descriptor.name}:  {command}")
            # The descriptor might be removed in the mean time. If this is the case stop execution.
            if wi.descriptor_alive:
                active_before_result = wi.is_active
                # before we move on, we need to store the current state of the task (or delete if it is done)
                await self.store_running_task_state(wi, origin_message)
                # inform the task about the result, which might trigger new tasks to execute
                new_commands = wi.handle_command_results(results)
                if new_commands:
                    # note: recursion depth is defined by the number of steps in a job description and should be safe.
                    await self.execute_task_commands(wi, new_commands)
                elif active_before_result and not wi.is_active:
                    # if this was the last result the task was waiting for, delete the task
                    await self.store_running_task_state(wi, origin_message)

        async def execute_in_order(task: Task[None]) -> None:
            # make sure the last execution is finished, before the new execution starts
            await task
            await execute_commands()

        # start execution of commands in own task to not block the task handler
        # note: the task is awaited finally in the timeout handler or context handler shutdown
        wi.update_task = asyncio.create_task(execute_in_order(wi.update_task) if wi.update_task else execute_commands())

    async def store_running_task_state(self, wi: RunningTask, origin_message: Optional[Message] = None) -> None:
        if wi.is_active:
            await self.running_task_db.update_state(wi, origin_message)
        elif wi.id in self.tasks:
            await self.running_task_db.delete(wi.id)

    async def list_all_pending_actions_for(self, subscriber: Subscriber) -> List[Action]:
        pending = map(lambda x: x.pending_action_for(subscriber), self.tasks.values())
        return [x for x in pending if x]

    # endregion

    # region periodic task checker

    async def check_overdue_tasks(self) -> None:
        """
        Called periodically by the system.
        In case there is an overdue task, an action error is injected into the task.
        """
        for task in list(self.tasks.values()):
            if task.is_active:  # task is still active
                if task.current_state.check_timeout():
                    if task.current_step.on_error == StepErrorBehaviour.Continue:
                        current_step = task.current_step.name
                        commands = task.move_to_next_state()
                        log.warning(
                            f"Task {task.id}: {task.descriptor.name} timed out in step "
                            f"{current_step}. Moving on to step: {task.current_step.name}."
                        )
                        await self.execute_task_commands(task, commands)
                    else:
                        log.warning(
                            f"Task {task.id}: {task.descriptor.name} timed out "
                            f"in step {task.current_step.name}. Stop the task."
                        )
                        task.end()
                        await self.store_running_task_state(task)
            # check again for active (might have changed for overdue tasks)
            if not task.is_active:
                if task.update_task:
                    await task.update_task
                del self.tasks[task.id]
                await self.running_task_db.delete(task.id)

    # endregion

    # region parse job data

    async def parse_job_file(self, file: TextIOWrapper) -> list[Job]:
        """
        Parse a file with job definitions.
        Every line is either a blank line, a comment or a job definition.

        Example
        # cron based trigger
        0 5 * * sat : reported name="foo" | desire name="bla"

        # cron based + event based trigger
        0 5 * * sat event_name : reported name="foo" | desire name="bla"

        :param file: the file handle to parse.
        :return: all parsed jobs.
        :raises: ParseError if the job can not be parsed
        """
        jobs = []
        with file as reader:
            for line in reader:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    job = await self.parse_job_line(f"file {file.name}", stripped, mutable=False)
                    jobs.append(job)
        return jobs

    async def parse_job_line(self, source: str, line: str, mutable: bool = True) -> Job:
        """
        Parse a single job line.
        :param source: the source of this line (just for naming purposes)
        :param line: the line of text
        :param mutable: defines if the resulting job is mutable or not.
        :return: the parsed jon
        """
        try:
            parts = re.split("\\s+", line.strip(), 5)
            if len(parts) != 6:
                raise ValueError(f"Invalid job {line}")
            uid = uuid_str(line.strip())[0:8]
            wait: Optional[Tuple[EventTrigger, timedelta]] = None
            trigger = TimeTrigger(" ".join(parts[0:5]))
            command = parts[5]
            # check if we also need to wait for an event: name_of_event : command
            if re.match("^[A-Za-z][A-Za-z0-9_\\-]*\\s*:", command):
                event, command = re.split("\\s*:\\s*", command, 1)
                wait = EventTrigger(event), timedelta(hours=24)
            await self.cli.evaluate_cli_command(command, replace_place_holder=False)
            return Job(uid, ExecuteCommand(command), trigger, timedelta(hours=1), wait, mutable)
        except CLIParseError as ex:
            raise ex
        except Exception as ex:
            raise ParseError(f"Can not parse job command line: {line}") from ex

    # endregion

    # region known task descriptors

    @staticmethod
    def known_jobs() -> list[Job]:
        return [
            Job(
                "example-job",
                ExecuteCommand("echo hello"),
                EventTrigger("run_job"),
                timedelta(seconds=10),
                mutable=False,
            ),
            Job(
                "example-wait-job",
                ExecuteCommand("sleep 10; echo I was started at @NOW@"),
                EventTrigger("run_job"),
                timedelta(seconds=10),
                (EventTrigger("wait"), timedelta(seconds=30)),
                mutable=False,
            ),
        ]

    @staticmethod
    def known_workflows() -> list[Workflow]:
        collect_steps = [
            Step("pre_collect", PerformAction("pre_collect"), timedelta(seconds=10)),
            Step("collect", PerformAction("collect"), timedelta(seconds=10)),
            Step("post_collect", PerformAction("post_collect"), timedelta(seconds=10)),
        ]
        cleanup_steps = [
            Step("pre_plan", PerformAction("pre_cleanup_plan"), timedelta(seconds=10)),
            Step("plan", PerformAction("cleanup_plan"), timedelta(seconds=10)),
            Step("post_plan", PerformAction("post_cleanup_plan"), timedelta(seconds=10)),
            Step("pre_clean", PerformAction("pre_cleanup"), timedelta(seconds=10)),
            Step("clean", PerformAction("cleanup"), timedelta(seconds=10)),
            Step("post_clean", PerformAction("post_cleanup"), timedelta(seconds=10)),
        ]
        metrics_steps = [
            Step("pre_metrics", PerformAction("pre_generate_metrics"), timedelta(seconds=10)),
            Step("metrics", PerformAction("generate_metrics"), timedelta(seconds=10)),
            Step("post_metrics", PerformAction("post_generate_metrics"), timedelta(seconds=10)),
        ]
        return [
            Workflow(
                uid="collect",
                name="collect",
                steps=collect_steps + metrics_steps,
                triggers=[EventTrigger("start_collect_workflow")],
            ),
            Workflow(
                uid="cleanup",
                name="cleanup",
                steps=cleanup_steps + metrics_steps,
                triggers=[EventTrigger("start_cleanup_workflow")],
            ),
            Workflow(
                uid="metrics",
                name="metrics",
                steps=metrics_steps,
                triggers=[EventTrigger("start_metrics_workflow")],
            ),
            Workflow(
                uid="collect_and_cleanup",
                name="collect_and_cleanup",
                steps=collect_steps + cleanup_steps + metrics_steps,
                triggers=[EventTrigger("start_collect_and_cleanup_workflow"), TimeTrigger("0 * * * *")],
            ),
        ]

    # endregion
