# /config/workspace/todo-app/backend/models/__init__.py
# Import models to make them accessible via the 'models' package
# and ensure they are registered with SQLAlchemy

# Existing models
from .user import User
from .website_account import WebsiteAccount
from .user_workflow import UserWorkflow, UserWorkflowTypeEnum, UserWorkflowStatusEnum

# New workflow-related models
from .workflow_spec import WorkflowSpec, TaskSpec, SpecDependency
from .workflow import Workflow, Task, TaskData, WorkflowData
from .instance import Instance

# You can optionally define an __all__ list to specify what gets imported
# when using 'from models import *', though explicit imports are generally preferred.
__all__ = [
    'User',
    'WebsiteAccount',
    'UserWorkflow', 'UserWorkflowTypeEnum', 'UserWorkflowStatusEnum',
    'WorkflowSpec', 'TaskSpec', 'SpecDependency',
    'Workflow', 'Task', 'TaskData', 'WorkflowData',
    'Instance'
]
