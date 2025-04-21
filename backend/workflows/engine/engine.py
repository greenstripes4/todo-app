# /config/workspace/todo-app/backend/workflows/engine/engine.py
import curses # Keep existing imports
import logging

from SpiffWorkflow.specs import SubWorkflow
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.specs.mixins.events.event_types import CatchingEvent
from SpiffWorkflow.bpmn import BpmnWorkflow
from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine
from SpiffWorkflow.bpmn.util.diff import (
    SpecDiff,
    diff_dependencies,
    diff_workflow,
    filter_tasks,
    migrate_workflow,
)
from SpiffWorkflow import TaskState

from .instance import Instance


# Ensure logger is set up for this module if not already configured elsewhere
logger = logging.getLogger(__name__)
# Example basic config if needed:
# if not logger.handlers:
#     logging.basicConfig(level=logging.INFO)


class BpmnEngine:

    def __init__(self, parser, serializer, script_env=None, instance_cls=None):

        self.parser = parser
        self.serializer = serializer
        # Ideally this would be recreated for each instance
        self._script_engine = PythonScriptEngine(script_env)
        self.instance_cls = instance_cls or Instance

    # --- Add Spec Methods (add_spec, add_collaboration, add_files) ---
    # ... (keep existing methods: add_spec, add_collaboration, add_files) ...
    def add_spec(self, process_id, bpmn_files, dmn_files):
        self.add_files(bpmn_files, dmn_files)
        try:
            spec = self.parser.get_spec(process_id)
            dependencies = self.parser.get_subprocess_specs(process_id)
        except ValidationException as exc:
            # Clear the process parsers so the files can be re-added
            # There's probably plenty of other stuff that should be here
            # However, our parser makes me mad so not investigating further at this time
            self.parser.process_parsers = {}
            raise exc
        spec_id = self.serializer.create_workflow_spec(spec, dependencies)
        logger.info(f'Added {process_id} with id {spec_id}')
        return spec_id

    def add_collaboration(self, collaboration_id, bpmn_files, dmn_files=None):
        self.add_files(bpmn_files, dmn_files)
        try:
            spec, dependencies = self.parser.get_collaboration(collaboration_id)
        except ValidationException as exc:
            self.parser.process_parsers = {}
            raise exc
        spec_id = self.serializer.create_workflow_spec(spec, dependencies)
        logger.info(f'Added {collaboration_id} with id {spec_id}')
        return spec_id

    def add_files(self, bpmn_files, dmn_files):
        self.parser.add_bpmn_files(bpmn_files)
        if dmn_files is not None:
            self.parser.add_dmn_files(dmn_files)

    # --- List/Delete Spec Methods ---
    # ... (keep existing methods: list_specs, delete_workflow_spec) ...
    def list_specs(self):
        return self.serializer.list_specs()

    def delete_workflow_spec(self, spec_id):
        self.serializer.delete_workflow_spec(spec_id)
        logger.info(f'Deleted workflow spec with id {spec_id}')

    # --- Workflow Instance Methods ---

    def start_workflow(self, spec_id):
        spec, sp_specs = self.serializer.get_workflow_spec(spec_id)
        wf = BpmnWorkflow(spec, sp_specs, script_engine=self._script_engine)
        wf_id = self.serializer.create_workflow(wf, spec_id)
        logger.info(f'Created workflow with id {wf_id}')
        # Get the instance using get_workflow to ensure callbacks are attached
        instance = self.get_workflow(wf_id)
        return instance

    def get_workflow(self, wf_id):
        """Retrieves a workflow instance and attaches persistence callbacks."""
        wf = self.serializer.get_workflow(wf_id)
        if wf is None:
             logger.error(f"Workflow with id {wf_id} not found by serializer.")
             # Consider raising an exception or returning None based on desired behavior
             raise ValueError(f"Workflow not found: {wf_id}") # Example: Raise error

        wf.script_engine = self._script_engine
        # Create the instance wrapper, passing the update_workflow method as the save callback
        instance = self.instance_cls(wf_id, wf, save=self.update_workflow)

        # --- Attach persistence callbacks ---
        self._attach_persistence_callbacks(instance)
        # --- End attaching callbacks ---

        return instance

    def update_workflow(self, instance):
        """Callback function used by the Instance object to save the workflow."""
        logger.info(f'Saving workflow {instance.wf_id} via update_workflow callback.')
        # The instance object holds the workflow, pass it to the serializer
        self.serializer.update_workflow(instance.workflow, instance.wf_id)

    # --- NEW HELPER METHOD for attaching callbacks ---
    def _attach_persistence_callbacks(self, instance):
        """
        Attaches callbacks to task ready and completed events to trigger
        workflow persistence via the instance's save method.
        """
        workflow = instance.workflow
        if not workflow:
            logger.warning(f"Cannot attach callbacks: workflow object is missing for instance {instance.wf_id}")
            return

        # Define the callback function that will be triggered by task events
        def on_task_event(workflow, task, *args):
            # Check if the instance and its workflow still exist
            if instance and instance.workflow:
                logger.info(f"Task event ({args[0] if args else 'unknown'}) for task '{task.task_spec.name}' in workflow {instance.wf_id}. Triggering save.")
                try:
                    # Call the save method configured on the instance object
                    instance.save()
                except Exception as e:
                    # Log errors during the save operation triggered by the callback
                    logger.error(f"Error saving workflow {instance.wf_id} during task event callback: {e}", exc_info=True)
                for child in task.children:
                    attach_task(child.task_spec)
                return True
            else:
                 logger.warning(f"Task event triggered but instance or workflow object not found for wf_id {instance.wf_id if instance else 'unknown'}.")

        # helper to attach callbacks to tasks in a workflow
        def attach_workflow(wf_spec):
            for name in wf_spec.task_specs:
                logger.debug(f"Attaching callbacks to tasks in workflow/subprocess {name}")
                # Connect the callback to the ready and completed events.
                # Note: SpiffWorkflow's event system doesn't have a built-in way
                # to check if a *specific* function is already connected.
                # We rely on get_workflow typically deserializing a new object graph,
                # thus avoiding duplicate connections in standard web request lifecycles.
                attach_task(wf_spec.task_specs[name])

        # helper to attach callbacks to a task
        def attach_task(task_spec):
            if task_spec.ready_event.is_connected(on_task_event):
                task_spec.ready_event.disconnect(on_task_event)
            task_spec.ready_event.connect(on_task_event, 'ready_event')
            if task_spec.completed_event.is_connected(on_task_event):
                task_spec.completed_event.disconnect(on_task_event)
            task_spec.completed_event.connect(on_task_event, 'completed_event')
            #if task_spec.started_event.is_connected(on_task_event):
            #    task_spec.started_event.disconnect(on_task_event)
            #task_spec.started_event.connect(on_task_event, 'started_event')
            if isinstance(task_spec, SubWorkflow):
                if task_spec.update_event.is_connected(on_task_event):
                    task_spec.update_event.disconnect(on_task_event)
                task_spec.update_event.connect(on_task_event, 'update_event')

        # Start the recursive attachment process
        attach_workflow(workflow.spec)
        logger.info(f"Persistence callbacks attached to tasks for workflow {instance.wf_id} and its subprocesses.")
    # --- END NEW HELPER METHOD ---


    def list_workflows(self, include_completed=False):
        return self.serializer.list_workflows(include_completed)

    def delete_workflow(self, wf_id):
        self.serializer.delete_workflow(wf_id)
        logger.info(f'Deleted workflow with id {wf_id}')

    # --- Diff/Migration Methods ---
    # ... (keep existing methods: diff_spec, diff_dependencies, diff_workflow, can_migrate, migrate_workflow) ...
    def diff_spec(self, original_id, new_id):
        original, _ = self.serializer.get_workflow_spec(original_id, include_dependencies=False)
        new, _ = self.serializer.get_workflow_spec(new_id, include_dependencies=False)
        return SpecDiff(self.serializer.registry, original, new)

    def diff_dependencies(self, original_id, new_id):
        _, original = self.serializer.get_workflow_spec(original_id, include_dependencies=True)
        _, new = self.serializer.get_workflow_spec(new_id, include_dependencies=True)
        return diff_dependencies(self.serializer.registry, original, new)

    def diff_workflow(self, wf_id, spec_id):
        wf = self.serializer.get_workflow(wf_id)
        spec, deps = self.serializer.get_workflow_spec(spec_id)
        return diff_workflow(self.serializer.registry, wf, spec, deps)

    def can_migrate(self, wf_diff, sp_diffs):

        def safe(result):
            mask = TaskState.COMPLETED|TaskState.STARTED
            tasks = result.changed + result.removed
            return len(filter_tasks(tasks, state=mask)) == 0

        for diff in sp_diffs.values():
            if diff is None or not safe(diff):
                return False
        return safe(wf_diff)

    def migrate_workflow(self, wf_id, spec_id, validate=True):

        wf = self.serializer.get_workflow(wf_id)
        spec, deps = self.serializer.get_workflow_spec(spec_id)
        wf_diff, sp_diffs = diff_workflow(self.serializer.registry, wf, spec, deps)

        if validate and not self.can_migrate(wf_diff, sp_diffs):
            raise Exception('Workflow is not safe to migrate!')

        migrate_workflow(wf_diff, wf, spec)
        for sp_id, sp in wf.subprocesses.items():
            migrate_workflow(sp_diffs[sp_id], sp, deps.get(sp.spec.name))
        wf.subprocess_specs = deps

        self.serializer.delete_workflow(wf_id)
        return self.serializer.create_workflow(wf, spec_id)

