from abc import ABC, abstractmethod
import time
import os

from mlcomp import MODE_ECONOMIC
from mlcomp.db.core import Session
from mlcomp.db.models import Task, Dag
from mlcomp.utils.config import Config
from mlcomp.db.providers import TaskProvider, ComputerProvider
from mlcomp.worker.executors.base.step import StepWrap


class Executor(ABC):
    _child = dict()

    session = None
    task_provider = None
    logger = None
    step = None

    def debug(self, message: str):
        self.step.debug(message)

    def info(self, message: str):
        self.step.info(message)

    def warning(self, message: str):
        self.step.warning(message)

    def error(self, message: str):
        self.step.error(message)

    def __call__(
            self, *, task: Task, task_provider: TaskProvider, dag: Dag
    ) -> dict:
        assert dag is not None, 'You must fetch task with dag_rel'

        self.task_provider = task_provider
        self.task = task
        self.dag = dag
        self.step = StepWrap(self.session, self.logger, task, task_provider)
        self.step.enter()

        if not task.debug and not MODE_ECONOMIC:
            self.wait_data_sync(task.computer_assigned)
        res = self.work()
        self.step.task_provider.commit()
        return res

    @staticmethod
    def kwargs_for_interface(executor: dict, config: Config, **kwargs):
        return {
            **executor['slot'], 'project_name': config['info']['project'],
            **kwargs
        }

    @abstractmethod
    def work(self) -> dict:
        pass

    @classmethod
    def _from_config(
            cls, executor: dict, config: Config, additional_info: dict
    ):
        return cls()

    @staticmethod
    def from_config(
            *, executor: str, config: Config, additional_info: dict,
            session: Session, logger
    ) -> 'Executor':
        if executor not in config['executors']:
            raise ModuleNotFoundError(
                f'Executor {executor} '
                f'has not been found'
            )

        executor = config['executors'][executor]
        child_class = Executor._child[executor['type']]
        # noinspection PyProtectedMember
        res = child_class._from_config(executor, config,
                                       additional_info)
        res.session = session
        res.logger = logger
        return res

    @staticmethod
    def register(cls):
        Executor._child[cls.__name__] = cls
        Executor._child[cls.__name__.lower()] = cls
        return cls

    @staticmethod
    def is_registered(cls: str):
        return cls in Executor._child

    def wait_data_sync(self, computer_assigned: str):
        self.info(f'Start data sync')
        provider = ComputerProvider(self.session)
        last_task_time = TaskProvider(self.session).last_succeed_time()
        self.info(f'Providers created')

        while True:
            computer = provider.by_name(computer_assigned)
            self.info(f'computer.last_synced = {computer.last_synced} '
                      f'last_task_time = {last_task_time}')

            if last_task_time is None or computer.last_synced > last_task_time:
                break

            provider.commit()
            time.sleep(1)
        self.info(f'Finish data sync')

    @staticmethod
    def is_trainable(type: str):
        variants = ['Catalyst']
        return type in (variants + [v.lower() for v in variants])


__all__ = ['Executor']
