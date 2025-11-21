from agisdk.REAL.browsergym.core.registration import register_task

from . import base, task_config

# Register each task using its canonical (version.name) identifier.
for canonical_id, (version, task_name) in task_config.TASK_INDEX.items():
    register_task(
        canonical_id,
        base.AbstractWebCloneTask,
        task_kwargs={"task_name": task_name, "task_version": version},
    )
