"""Base utilities for task-based installer.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import List, Set, Type, TypeVar, Optional
    T = TypeVar("T")


class State:
    """A generic dictionary that associate a type to an its instance.
    """

    def __init__(self) -> None:
        self.data = {}

    def clear(self) -> None:
        """Clear the state dictionary.
        """
        self.data.clear()

    def get(self, ty: "Type[T]") -> "Optional[T]":
        """Get the associated value of a given type.

        :param ty: The type of the value to get.
        :return: The instance of the given type, none if not present.
        """
        return self.data.get(ty)
    
    def insert(self, value: object) -> None:
        """Insert an instance in this dictionary.

        :param value: The value to associated to its type.
        """
        self.data[type(value)] = value

    def __contains__(self, ty: type) -> bool:
        return ty in self.data

    def __getitem__(self, ty: "Type[T]") -> "T":
        return self.data[ty]


class TaskError(Exception):
    """A generic task error with a code and 
    """


class Task:
    """Represent a task that can be run in the installer.

    Subclasses should specify which 
    """

    def setup(self, state: "State") -> None:
        """Initialize the installer's state data, this is called when
        the task is added to an installer. The order of these calls
        should not be important, and conflicting states are not 
        handled by installers.

        :param state: The global installer's state data.
        """
    
    def execute(self, state: "State") -> None:
        """Execute the task with a given piece of data.

        :param state: The installer's state data, this can be used to 
        transmit data to future tasks that requires parameters. This 
        data can also be used to alt the installer and resume it.
        :raises NotImplementedError: Raised if this function is not
        implemented by subclasses.
        """
        raise NotImplementedError


class Watcher:
    """Base class for a watcher of the install process.
    """

    def on_task_begin(self, task: "Task") -> None:
        """Called when a task is going to be executed.
        """

    def on_task_end(self, task: "Task") -> None:
        """Called when a task has been successfully executed.
        """
    
    def on_event(self) -> None:
        """Called when the current task triggers an event.
        """


class Installer:
    """A task-based installer.
    """

    def __init__(self) -> None:
        self._tasks: List[Task] = []
        self._state: State = State()
        self._watchers: Set[Watcher] = set()

    def insert_task(self, task: "Task", index: int) -> None:
        """Insert a task at a given index.

        :param task: The task to insert at.
        :param index: The index to insert the task at. Note that, like
        for builtin lists, an index to big will just add the task at
        the end.
        """
        self._tasks.insert(index, task)
        task.setup(self._state)

    def append_task(self, task: "Task", *, 
        after: "Optional[Type[Task]]" = None
    ) -> None:
        """Append a task to be executed by this installer.

        :param task: The task to add to this installer.
        :param after: If defined, the task will be appended after the
        given task type.
        """
        if after is not None:
            for i, task in enumerate(self._tasks):
                if type(task) is after:
                    self.insert_task(task, i + 1)
        self.insert_task(task, len(self._tasks))
    
    def prepend_task(self, task: "Task", *, 
        before: "Optional[Type[Task]]" = None
    ) -> None:
        """Prepend a task to be executed by this installer.

        :param task: The task to add to this installer.
        :param before: If defined, the task will be prepended before
        the given task type.
        """
        if before is not None:
            for i, task in enumerate(self._tasks):
                if type(task) is before:
                    self.insert_task(task, i)
        self.insert_task(task, 0)

    def add_watcher(self, watcher: "Watcher") -> None:
        """Add a watcher to the installer. Adding the same watcher
        twice overrides the last instance.
        """
        self._watchers.add(watcher)
    
    def remove_watcher(self, watcher: "Watcher") -> None:
        """Remove a watcher from the installer.
        """
        self._watchers.remove(watcher)

    def reset(self) -> None:
        """Reset the internal state and re-init all tasks.
        """
        self._state.clear()
        for task in self._tasks:
            task.setup(self._state)

    def install(self) -> None:
        """Sequentially execute the tasks of this installer.
        """

        for task in self._tasks:

            for watcher in self._watchers:
                watcher.on_task_begin(task)

            task.execute(self._state)

            for watcher in self._watchers:
                watcher.on_task_end(task)