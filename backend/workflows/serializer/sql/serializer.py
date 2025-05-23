# /config/workspace/todo-app/backend/workflows/serializer/sql/serializer.py
import logging
from uuid import uuid4, UUID
import json # Keep json for potential direct use, though SQLAlchemy handles much of it

from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.specs.mixins.subworkflow_task import SubWorkflowTask
from SpiffWorkflow import TaskState
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func # Import func for potential use, though models use it

# Import your app's db object and models
from app import db
from models.instance import Instance
from models.workflow import Workflow, Task # Task needed for subprocess logic and instance update
# Removed TaskData, WorkflowData as they aren't directly used in the serializer logic shown
from models.workflow_spec import WorkflowSpec, TaskSpec, SpecDependency
# --- Import UserWorkflow model and Enum ---
from models.user_workflow import UserWorkflow, UserWorkflowStatusEnum # Make sure DELETED is in this Enum

logger = logging.getLogger(__name__)


class SqlSerializer(BpmnWorkflowSerializer):
    """
    Serializes SpiffWorkflow objects to and from a relational database
    using SQLAlchemy ORM models.
    """

    # Remove the static initialize method - Schema management should be external (e.g., Flask-Migrate)
    # @staticmethod
    # def initialize(db): ...

    def __init__(self, db_session, **kwargs):
        """
        Initializes the serializer.

        :param db_session: The SQLAlchemy session object (e.g., app.db.session).
                           Note: We actually store the db object itself for session access.
        """
        super().__init__(**kwargs)
        # Store the db object from Flask-SQLAlchemy
        self.db = db_session # Parameter name kept as db_session for clarity, but it's the db object
        # No dbname needed anymore

    # --- Workflow Spec Methods ---

    def create_workflow_spec(self, spec, dependencies):
        """
        Creates or retrieves a workflow specification and its dependencies.
        Handles the database transaction.
        """
        try:
            spec_id, new = self._create_workflow_spec_internal(spec)
            if new and dependencies:
                # Recursively create dependencies and collect relationships
                pairs = self._resolve_spec_dependencies(spec_id, spec, dependencies)
                if pairs:
                    self._set_spec_dependencies_internal(pairs)

            self.db.session.commit()
            logger.info(f"Committed creation/update for WorkflowSpec '{spec.name}' (ID: {spec_id})")
            return spec_id
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error creating workflow spec '{spec.name}': {e}", exc_info=True)
            raise # Re-raise after logging and rollback

    def _create_workflow_spec_internal(self, spec):
        """
        Internal method to find or create a WorkflowSpec record.
        Does NOT commit the session.
        Assumes spec.name uniquely identifies a spec for lookup within serialization.
        """
        # Query based on unique properties stored within serialization JSON
        # Using json path expression requires specific DB support (PostgreSQL JSONB works well)
        # Note: Consider adding a dedicated 'name' column to WorkflowSpec for efficient lookup
        # if this becomes a performance bottleneck.
        existing_spec = WorkflowSpec.query.filter(
            WorkflowSpec.serialization['name'].as_string() == spec.name
        ).first()

        if existing_spec:
            logger.debug(f"Found existing WorkflowSpec: Name='{spec.name}', ID={existing_spec.id}")
            return existing_spec.id, False
        else:
            dct = self.to_dict(spec) # Use the appropriate converter
            # Add 'name' to top level of dict if needed for query, or rely on JSON path
            # dct['name'] = spec.name # Already done by converter if spec has 'name' attribute
            new_spec = WorkflowSpec(serialization=dct)
            # ID is generated by DB (server_default)
            self.db.session.add(new_spec)
            self.db.session.flush() # Flush to get the generated ID
            logger.info(f"Created new WorkflowSpec: Name='{spec.name}', ID={new_spec.id}")
            return new_spec.id, True

    def _resolve_spec_dependencies(self, parent_id, parent_spec, all_dependencies):
        """
        Recursively finds/creates child specs and returns dependency pairs (parent_id, child_id).
        Does NOT commit the session.
        """
        pairs = set()
        # Find subworkflow tasks in the parent spec
        for task_spec in parent_spec.task_specs.values():
            if isinstance(task_spec, SubWorkflowTask) and task_spec.spec in all_dependencies:
                child_spec_obj = all_dependencies[task_spec.spec]
                # Ensure child spec exists in DB
                child_id, new_child = self._create_workflow_spec_internal(child_spec_obj)
                # Add dependency pair
                pairs.add((parent_id, child_id))
                # If the child was newly created, recurse to find its dependencies
                if new_child:
                    # Pass only relevant dependencies for the child if possible, or all_dependencies
                    child_pairs = self._resolve_spec_dependencies(child_id, child_spec_obj, all_dependencies)
                    pairs.update(child_pairs)
        return pairs

    def _set_spec_dependencies_internal(self, pairs):
        """Internal method to add SpecDependency records. Does NOT commit."""
        added_count = 0
        for parent_id, child_id in pairs:
            # Avoid adding duplicates if they already exist
            exists = SpecDependency.query.get((parent_id, child_id))
            if not exists:
                dep = SpecDependency(parent_id=parent_id, child_id=child_id)
                self.db.session.add(dep)
                added_count += 1
        if added_count > 0:
             logger.info(f"Added {added_count} spec dependencies.")
        # Commit happens in the public calling method

    def get_workflow_spec(self, spec_id, include_dependencies=True):
        """Retrieves a workflow specification, optionally including dependencies."""
        try:
            spec_obj = WorkflowSpec.query.get(spec_id)
            if not spec_obj:
                logger.warning(f"WorkflowSpec with id {spec_id} not found.")
                return None, {} # Or raise an error

            spec = self.from_dict(spec_obj.serialization) # Use appropriate converter
            subprocess_specs = {}

            if include_dependencies:
                # Use the relationship defined in the model
                # Assumes child spec serialization contains 'name'
                # Use .all() on the lazy dynamic relationship
                for dep in spec_obj.child_dependencies.all():
                     child_spec_record = dep.child_spec # Access related spec via relationship
                     if child_spec_record and 'name' in child_spec_record.serialization:
                         child_name = child_spec_record.serialization['name']
                         subprocess_specs[child_name] = self.from_dict(child_spec_record.serialization)
                     else:
                         logger.warning(f"Could not find name or child spec for dependency from {spec_id} to {dep.child_id}")

            return spec, subprocess_specs
        except Exception as e:
            logger.error(f"Error getting workflow spec {spec_id}: {e}", exc_info=True)
            # No transaction to rollback, just raise
            raise

    def list_specs(self):
        """Lists available workflow specifications."""
        try:
            # Extract 'name' from the JSONB serialization field
            specs = WorkflowSpec.query.with_entities(
                WorkflowSpec.id,
                WorkflowSpec.serialization['name'].as_string().label('name')
                # Add WorkflowSpec.serialization['file'].as_string().label('filename') if needed
            ).order_by(WorkflowSpec.serialization['name'].as_string()).all()
            # Return list of tuples (id, name)
            return [(s.id, s.name) for s in specs]
        except Exception as e:
            logger.error(f"Error listing workflow specs: {e}", exc_info=True)
            raise

    def delete_workflow_spec(self, spec_id):
        """Deletes a workflow specification if it's not in use."""
        try:
            spec_obj = WorkflowSpec.query.get(spec_id)
            if not spec_obj:
                logger.warning(f"WorkflowSpec {spec_id} not found for deletion.")
                return False # Indicate not found

            # Check if any workflows use this spec
            # The ForeignKey constraint in Workflow model should prevent deletion if used,
            # leading to an IntegrityError on commit.
            self.db.session.delete(spec_obj)
            self.db.session.commit()
            logger.info(f"Deleted WorkflowSpec {spec_id}")
            return True # Indicate success
        except IntegrityError:
            self.db.session.rollback()
            logger.warning(f"Cannot delete WorkflowSpec {spec_id}: It is referenced by existing Workflows.")
            return False # Indicate failure due to dependencies
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error deleting workflow spec {spec_id}: {e}", exc_info=True)
            raise

    # --- Workflow Instance Methods ---

    # --- NEW HELPER METHOD ---
    def _count_ready_tasks(self, workflow):
        """Counts tasks in the READY state within a workflow object."""
        # Manually count tasks with state value 16 (TaskState.READY)
        # This handles cases where the state might be an int or a TaskState enum
        tasks_with_state_ready = 0
        # Fallback to manual iteration if get_tasks fails or is unreliable here
        # logger.warning(f"get_tasks(TaskState.READY) cannot work in SqlSerializer, falling back to manual count.")
        all_tasks = workflow.get_tasks() # Get all tasks
        for task in all_tasks:
            # Check both TaskState enum and integer value for robustness
            if (isinstance(task.state, TaskState) and task.state == TaskState.READY) or \
                (isinstance(task.state, int) and task.state == TaskState.READY): # [TODO] 'int' object has no attribute 'value' for TaskState.READY.value here
                tasks_with_state_ready += 1
        # tasks_with_state_ready = len(workflow.get_tasks(TaskState.READY))
        return tasks_with_state_ready
    # --- END NEW HELPER METHOD ---

    def create_workflow(self, workflow, spec_id):
        """Creates a new workflow instance and its subprocesses."""
        try:
            # Ensure the spec exists
            spec_obj = WorkflowSpec.query.get(spec_id)
            if not spec_obj:
                 raise ValueError(f"WorkflowSpec with id {spec_id} not found.")

            # Convert main workflow
            dct = self.to_dict(workflow)

            # Create main workflow record
            # Generate a new UUID for the main workflow
            wf_id = uuid4()
            new_wf = Workflow(id=wf_id, workflow_spec_id=spec_id, serialization=dct)
            self.db.session.add(new_wf)
            logger.info(f"Creating Workflow ID: {wf_id} for Spec ID: {spec_id}")

            # Handle subprocesses if any
            if workflow.subprocesses:
                # Get spec dependencies to find child spec IDs
                # Use .all() on the lazy dynamic relationship
                spec_deps = spec_obj.child_dependencies.all()
                # Create a map of child spec name -> child spec id
                child_spec_map = {
                    dep.child_spec.serialization['name']: dep.child_id
                    for dep in spec_deps if dep.child_spec and 'name' in dep.child_spec.serialization
                }

                for sp_task_id, sp_workflow in workflow.subprocesses.items():
                    sp_spec_name = sp_workflow.spec.name
                    if sp_spec_name not in child_spec_map:
                        raise ValueError(f"Cannot find spec dependency for subprocess spec name '{sp_spec_name}'")

                    sp_spec_id = child_spec_map[sp_spec_name]
                    sp_dct = self.to_dict(sp_workflow) # Use appropriate converter

                    # Use the task_id from the parent as the ID for the subprocess workflow record
                    # Ensure sp_task_id is a UUID
                    sp_wf_id = UUID(str(sp_task_id)) if not isinstance(sp_task_id, UUID) else sp_task_id
                    sp_wf = Workflow(id=sp_wf_id, workflow_spec_id=sp_spec_id, serialization=sp_dct)
                    self.db.session.add(sp_wf)
                    logger.info(f"Creating Subprocess Workflow ID: {sp_wf_id} (Task ID) for Spec ID: {sp_spec_id}")

            # Create the associated Instance record
            # The Instance ID must match the Workflow ID

            # Use the helper method to count ready tasks
            initial_ready_tasks = self._count_ready_tasks(workflow)
            logger.info(f"Initial ready task count: {initial_ready_tasks}")

            instance = Instance(
                id=wf_id, # Use the same ID as the Workflow
                spec_name=spec_obj.serialization.get('name', 'Unknown'), # Get name from spec serialization
                # Calculate initial ready tasks for the instance record using the helper
                active_tasks=initial_ready_tasks,
                # started is server_default
            )
            self.db.session.add(instance)
            logger.info(f"Creating Instance record for Workflow ID: {wf_id}")

            # --- UserWorkflow creation removed from here ---

            self.db.session.commit()
            logger.info(f"Committed creation for Workflow ID: {wf_id}")
            return wf_id # Return the main workflow ID
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error creating workflow for spec {spec_id}: {e}", exc_info=True)
            raise

    def get_workflow(self, wf_id, include_dependencies=True):
        """Retrieves a workflow instance, optionally including subprocesses."""
        try:
            wf_obj = Workflow.query.get(wf_id)
            if not wf_obj:
                logger.warning(f"Workflow with id {wf_id} not found.")
                return None

            # Initial deserialization of the main workflow
            # The `from_dict` method might need modification if it expects subprocesses
            # to be passed in during deserialization.
            workflow = self.from_dict(wf_obj.serialization)
            workflow.id = wf_obj.id # Ensure ID is set on the object

            if include_dependencies:
                # 1. Get Subprocess Specs (using the spec relationship)
                spec_obj = wf_obj.workflow_spec # Access related spec via relationship
                subprocess_specs = {}
                if spec_obj:
                    # Use .all() on the lazy dynamic relationship
                    for dep in spec_obj.child_dependencies.all():
                        child_spec_record = dep.child_spec
                        if child_spec_record and 'name' in child_spec_record.serialization:
                            child_name = child_spec_record.serialization['name']
                            subprocess_specs[child_name] = self.from_dict(child_spec_record.serialization)
                workflow.subprocess_specs = subprocess_specs # Attach to workflow object

                # 2. Get Subprocess Workflow Instances
                # Find task IDs that represent subprocesses within the main workflow object
                subproc_task_ids = []
                for task in workflow.get_tasks(): # Iterate through all tasks in the deserialized workflow
                    if isinstance(task.task_spec, SubWorkflowTask): # Check if task spec is for a subworkflow
                         # Ensure task.id is a UUID for the query
                        task_uuid = UUID(str(task.id)) if not isinstance(task.id, UUID) else task.id
                        subproc_task_ids.append(task_uuid)


                if subproc_task_ids:
                    # Query the Workflow table for records matching these task IDs
                    sub_workflow_records = Workflow.query.filter(Workflow.id.in_(subproc_task_ids)).all()
                    sub_workflows_map = {wf.id: wf for wf in sub_workflow_records}

                    # Deserialize and attach subprocesses
                    workflow.subprocesses = {} # Clear any initial state
                    for task_id_uuid in subproc_task_ids:
                        # Find the parent task that spawned this subprocess using its original ID form
                        parent_task = workflow.get_task_from_id(task_id_uuid) # Assumes get_task_from_id handles UUIDs

                        if parent_task and task_id_uuid in sub_workflows_map:
                            sub_record = sub_workflows_map[task_id_uuid]
                            # Deserialize the subprocess, linking it to the parent task and top workflow
                            sp = self.from_dict(
                                sub_record.serialization,
                                task=parent_task,
                                top_workflow=workflow
                            )
                            sp.id = sub_record.id # Ensure ID is set
                            workflow.subprocesses[parent_task.id] = sp # Use original task ID as key
                        elif not parent_task:
                            logger.warning(f"Could not find parent task with id {task_id_uuid} in workflow {wf_id}")
                        else: # task exists but record doesn't
                             logger.warning(f"Subprocess workflow record not found for task id {task_id_uuid} (parent workflow {wf_id})")

            return workflow
        except Exception as e:
            logger.error(f"Error getting workflow {wf_id}: {e}", exc_info=True)
            raise

    def update_workflow(self, workflow, wf_id=None):

        """Updates a workflow instance and its subprocesses."""
        if wf_id is None:
            wf_id = workflow.id # Get ID from workflow object if not passed
        # Ensure wf_id is UUID
        wf_id = UUID(str(wf_id)) if not isinstance(wf_id, UUID) else wf_id
        # Convert UUID to string for UserWorkflow lookup
        wf_id_str = str(wf_id)
        try:
            # --- Update Main Workflow ---
            wf_obj = Workflow.query.get(wf_id)
            if not wf_obj:
                raise ValueError(f"Workflow with id {wf_id} not found for update.")

            dct = self.to_dict(workflow) # Serialize the updated main workflow state
            wf_obj.serialization = dct
            logger.debug(f"Updating main Workflow {wf_id} serialization.")

            # --- Update/Create Subprocesses ---
            if workflow.subprocesses:
                 # Get spec dependencies to find child spec IDs if needed for new subprocesses
                # Use .all() on the lazy dynamic relationship
                spec_deps = wf_obj.workflow_spec.child_dependencies.all()
                child_spec_map = {
                    dep.child_spec.serialization['name']: dep.child_id
                    for dep in spec_deps if dep.child_spec and 'name' in dep.child_spec.serialization
                }

                # Get IDs of existing subprocess workflow records linked via tasks
                current_sp_task_ids_uuid = {UUID(str(tid)) for tid in workflow.subprocesses.keys()}
                existing_sp_records = Workflow.query.filter(Workflow.id.in_(current_sp_task_ids_uuid)).all()
                existing_sp_map = {rec.id: rec for rec in existing_sp_records}


                for sp_task_id, sp_workflow in workflow.subprocesses.items():
                    sp_task_id_uuid = UUID(str(sp_task_id)) if not isinstance(sp_task_id, UUID) else sp_task_id
                    sp_dct = self.to_dict(sp_workflow) # Serialize subprocess state

                    if sp_task_id_uuid in existing_sp_map:
                        # Update existing subprocess workflow
                        sp_wf_obj = existing_sp_map[sp_task_id_uuid]
                        sp_wf_obj.serialization = sp_dct
                        logger.debug(f"Updating subprocess Workflow {sp_task_id_uuid} serialization.")
                    else:
                        # Create new subprocess workflow (e.g., if a new subworkflow task was reached)
                        sp_spec_name = sp_workflow.spec.name
                        if sp_spec_name not in child_spec_map:
                             raise ValueError(f"Cannot find spec dependency for new subprocess spec name '{sp_spec_name}'")
                        sp_spec_id = child_spec_map[sp_spec_name]

                        sp_wf = Workflow(id=sp_task_id_uuid, workflow_spec_id=sp_spec_id, serialization=sp_dct)
                        self.db.session.add(sp_wf)
                        logger.info(f"Creating new subprocess Workflow {sp_task_id_uuid} during update.")

            # --- Update Instance Record ---
            instance_obj = Instance.query.get(wf_id)
            if instance_obj:
                # Update active tasks count based on READY state using the helper
                instance_obj.active_tasks = self._count_ready_tasks(workflow)
                # Check if the workflow object has a completion timestamp attribute
                if hasattr(workflow, 'completed_at') and workflow.completed_at:
                    instance_obj.ended = workflow.completed_at
                elif workflow.is_completed(): # Check completion status otherwise
                    instance_obj.ended = db.func.now() # Set end time if completed now
                else:
                    instance_obj.ended = None # Ensure ended is null if not completed

                # 'updated' column updates automatically via onupdate
                logger.debug(f"Updating Instance {wf_id} record.")
            else:
                # This case might indicate an inconsistency, log a warning
                logger.warning(f"Instance record for workflow {wf_id} not found during update.")
                # Optionally create it if it should exist
                # spec_name = wf_obj.workflow_spec.serialization.get('name', 'Unknown')
                # instance = Instance(...)
                # self.db.session.add(instance)

            # --- Update UserWorkflow Record ---
            user_workflow = UserWorkflow.query.filter_by(workflow_id=wf_id_str).first()
            if user_workflow:
                if workflow.is_completed():
                    logger.info(f"Workflow {wf_id_str} completed. Updating UserWorkflow.")
                    if workflow.success:
                        completed_tasks = workflow.get_tasks(state=TaskState.COMPLETED)
                        for completed_task in completed_tasks:
                            if completed_task.task_spec.name.startswith('End') and completed_task.task_spec.name.endswith('Failed'):
                                logger.info(f"Workflow {wf_id_str} failed gracefully.")
                                user_workflow.workflow_status = UserWorkflowStatusEnum.FAILED
                        if user_workflow.workflow_status != UserWorkflowStatusEnum.FAILED:
                            logger.info(f"Workflow {wf_id_str} completed gracefully.")
                            user_workflow.workflow_status = UserWorkflowStatusEnum.COMPLETED
                    else:
                        if user_workflow.workflow_status != UserWorkflowStatusEnum.TERMINATED:
                            user_workflow.workflow_status = UserWorkflowStatusEnum.FAILED
                    user_workflow.active_tasks = [] # Clear active tasks on completion
                else:
                    # Check if the status is already one of the terminal states before setting to RUNNING
                    terminal_statuses = {
                        UserWorkflowStatusEnum.TERMINATED,
                        UserWorkflowStatusEnum.FAILED,
                        UserWorkflowStatusEnum.CANCELLED,
                        UserWorkflowStatusEnum.DELETED
                    }
                    if user_workflow.workflow_status not in terminal_statuses:
                        logger.info(f"Workflow {wf_id_str} is running. Updating UserWorkflow.")
                        user_workflow.workflow_status = UserWorkflowStatusEnum.RUNNING
                        # Use TaskState.READY instead of STARTED directly
                        started_tasks = [
                            task.task_spec.name for task in workflow.get_tasks(state=TaskState.READY)
                        ]
                        user_workflow.active_tasks = started_tasks
                        logger.debug(f"Setting active_tasks for {wf_id_str} to: {started_tasks}")
                    else:
                         logger.info(f"Workflow {wf_id_str} is in a terminal state ({user_workflow.workflow_status.value}). Skipping status update to RUNNING.")
                         # Decide if active_tasks should be cleared or kept in terminal states other than COMPLETED/DELETED
                         # user_workflow.active_tasks = [] # Optionally clear here too


                # Add to session to ensure changes are tracked
                self.db.session.add(user_workflow)
            else:
                logger.warning(f"UserWorkflow record for workflow_id {wf_id_str} not found during update.")
                # Consider if you need to create it here if it might be missing,
                # though typically it should exist if created by `create_workflow` or another process.

            self.db.session.commit()
            logger.info(f"Committed update for Workflow ID: {wf_id}")
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error updating workflow {wf_id}: {e}", exc_info=True)
            raise

    def list_workflows(self, include_completed=False):
        """Lists workflow instances."""
        try:
            query = Instance.query
            if not include_completed:
                query = query.filter(Instance.ended.is_(None))

            instances = query.order_by(Instance.started.desc()).all()

            # Return data in the format expected by the caller (e.g., API response)
            return [
                {
                    "id": i.id,
                    "spec_name": i.spec_name,
                    "active_tasks": i.active_tasks,
                    "started": i.started.isoformat() if i.started else None,
                    "updated": i.updated.isoformat() if i.updated else None,
                    "ended": i.ended.isoformat() if i.ended else None,
                }
                for i in instances
            ]
        except Exception as e:
            logger.error(f"Error listing workflows: {e}", exc_info=True)
            raise

    def delete_workflow(self, wf_id):
        """
        Deletes a workflow instance and its related SpiffWorkflow data (via cascade),
        and updates the corresponding UserWorkflow record status to DELETED.
        """
        # Ensure wf_id is UUID
        wf_id = UUID(str(wf_id)) if not isinstance(wf_id, UUID) else wf_id
        wf_id_str = str(wf_id) # For UserWorkflow lookup

        try:
            wf_obj = Workflow.query.get(wf_id)
            if not wf_obj:
                logger.warning(f"Workflow {wf_id} not found for deletion.")
                return False # Indicate not found

            # --- Update UserWorkflow Record Status ---
            user_workflow = UserWorkflow.query.filter_by(workflow_id=wf_id_str).first()
            if user_workflow:
                logger.info(f"Marking UserWorkflow record for workflow_id {wf_id_str} as DELETED.")
                user_workflow.workflow_status = UserWorkflowStatusEnum.DELETED
                user_workflow.active_tasks = []
                self.db.session.add(user_workflow) # Ensure the update is tracked
            else:
                 logger.warning(f"UserWorkflow record for workflow_id {wf_id_str} not found during deletion/update.")

            # --- Delete Main Workflow and Cascade SpiffWorkflow Data ---
            # Deleting the main Workflow object should trigger cascades defined in the models
            # for related SpiffWorkflow entities like Instance, Task, TaskData, WorkflowData.
            logger.info(f"Deleting Workflow {wf_id} and associated SpiffWorkflow data via cascade.")
            self.db.session.delete(wf_obj)

            self.db.session.commit()
            logger.info(f"Committed deletion for Workflow ID: {wf_id} and updated UserWorkflow status.")
            return True # Indicate success
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Error deleting workflow {wf_id}: {e}", exc_info=True)
            raise

    # Remove the execute method - session management is handled in each public method
    # def execute(self, func, *args, **kwargs): ...
