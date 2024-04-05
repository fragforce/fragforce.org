from django_workflow_engine import COMPLETE, Step, Workflow
from django_workflow_engine.tests.tasks import BasicTask

simple_workflow = Workflow(
    name="simple_workflow",
    steps=[
        Step(
            step_id="log_hello_world",
            task_name="log_message",
            targets=["log_name"],
            start=True,
            task_info={
                "message": "Hello World!",
            },
        ),
        Step(
            step_id="log_name",
            task_name="log_message",
            targets=COMPLETE,
            task_info={
                "message": "Sam",
            },
        ),
    ],
)
