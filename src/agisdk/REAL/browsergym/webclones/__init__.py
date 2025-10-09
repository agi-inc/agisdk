from agisdk.REAL.browsergym.core.registration import register_task
from . import task_config, base

# register the RealBench benchmark
for task_id in task_config.TASKS:
    gym_id = f"webclones.{task_id}"
    # Only register with the task_id as a required parameter
    # run_id will be provided at runtime as needed for leaderboard submissions
    register_task(
        gym_id,
        base.AbstractWebCloneTask,
        task_kwargs={"task_id": task_id}
    )

# Register audio tasks if available
for task_id in task_config.AUDIO_TASKS:
    gym_id = f"audio.{task_id}"
    # Register audio tasks with audio prefix
    register_task(
        gym_id,
        base.AbstractWebCloneTask,
        task_kwargs={"task_id": task_id, "use_audio": True}
    )
