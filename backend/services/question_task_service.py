"""登记和取消当前 API 进程中的交互式问答任务。

当前生产配置使用单个 Uvicorn worker，因此进程内注册表可以精确取消任务。
若后续扩展为多 worker 或多容器，需将注册表换为 Redis 或共享任务队列。
"""

import asyncio
from dataclasses import dataclass, field
from threading import Event, Lock


@dataclass
class ActiveQuestionTask:
    task: asyncio.Task
    conversation_id: int
    user_message_id: int
    assistant_message_id: int | None = None
    completed: Event = field(default_factory=Event)


_active_tasks: dict[tuple[int, str], ActiveQuestionTask] = {}
_registry_lock = Lock()


def is_question_task_active(user_id: int, request_id: str) -> bool:
    with _registry_lock:
        entry = _active_tasks.get((user_id, request_id))
    return bool(entry and not entry.task.done())


def register_question_task(
    user_id: int,
    request_id: str,
    task: asyncio.Task,
    *,
    conversation_id: int,
    user_message_id: int,
) -> ActiveQuestionTask:
    entry = ActiveQuestionTask(
        task=task,
        conversation_id=conversation_id,
        user_message_id=user_message_id,
    )
    with _registry_lock:
        _active_tasks[(user_id, request_id)] = entry
    return entry


def complete_question_task(
    user_id: int,
    request_id: str,
    task: asyncio.Task,
    *,
    assistant_message_id: int | None = None,
) -> None:
    key = (user_id, request_id)
    with _registry_lock:
        entry = _active_tasks.get(key)
        if not entry or entry.task is not task:
            return
        entry.assistant_message_id = assistant_message_id
        entry.completed.set()
        _active_tasks.pop(key, None)


async def cancel_question_task(user_id: int, request_id: str) -> dict:
    with _registry_lock:
        entry = _active_tasks.get((user_id, request_id))
    if not entry or entry.task.done():
        return {"cancelled": False}

    try:
        entry.task.get_loop().call_soon_threadsafe(entry.task.cancel)
    except RuntimeError:
        return {"cancelled": False}
    completed = await asyncio.to_thread(entry.completed.wait, 3)
    if not completed:
        # 页面仍可停止等待；后端会在任务退出后继续完成取消记录。
        pass
    return {
        "cancelled": True,
        "conversation_id": entry.conversation_id,
        "user_message_id": entry.user_message_id,
        "assistant_message_id": entry.assistant_message_id,
    }
