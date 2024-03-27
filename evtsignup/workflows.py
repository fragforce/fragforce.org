from django_workflow_engine import Step, Workflow

onboard_contractor = Workflow(
    name="onboard_contractor",
    steps=[
        Step(...),
        Step(...),
        Step(...),
    ],
)

onboard_perm = Workflow(
    name="onboard_perm",
    steps=[
        ...
    ],
)
