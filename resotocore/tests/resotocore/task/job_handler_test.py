from typing import List, Optional, Dict

from resotocore.task import TaskHandler
from resotocore.task.task_description import RunningTask, Job, Workflow, TaskDescriptorId
from resotocore.util import first


class InMemJobHandler(TaskHandler):
    def __init__(self) -> None:
        self.jobs: List[Job] = []
        self.started_tasks: List[TaskDescriptorId] = []

    async def list_jobs(self) -> List[Job]:
        return self.jobs

    async def list_workflows(self) -> List[Workflow]:
        return []

    async def add_job(self, job: Job) -> None:
        self.jobs.append(job)

    async def delete_job(self, job_id: str) -> Optional[Job]:
        job: Optional[Job] = first(lambda j: j.id == job_id, self.jobs)
        if job:
            self.jobs.remove(job)
            return job
        else:
            return None

    async def parse_job_line(
        self, source: str, line: str, env: Optional[Dict[str, str]] = None, mutable: bool = True
    ) -> Job:
        raise NotImplementedError()

    async def start_task_by_descriptor_id(self, uid: TaskDescriptorId) -> Optional[RunningTask]:
        self.started_tasks.append(uid)
        return None

    async def running_tasks(self) -> List[RunningTask]:
        raise NotImplementedError()
