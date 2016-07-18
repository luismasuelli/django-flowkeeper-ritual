###################################################################################
#                                                                                 #
# Workflow logic will be coded here, just to get rid of dirty code in the models. #
#                                                                                 #
###################################################################################

from __future__ import unicode_literals
from django.utils.translation import ugettext_lazy as _
from django.utils.six import string_types
from cantrips.iteration import iterable
from . import exceptions, models

class Workflow(object):

    class PermissionsChecker(object):
        """
        Permissions checks raise different subclasses of PermissionDenied.

        These checks are all performed against the associated document (since
          each workflow instance must be tied to a specific model or, say, document,
          these points can be addressed easily).
        """

        @classmethod
        def can_instantiate_workflow(cls, workflow_instance, user):
            """
            Verifies the user can create a workflow instance, given the instance and user.
            :param workflow_instance: The instance to check (will be already valid).
            :param user: The user to check
            :return: nothing
            """

            permission = workflow_instance.workflow_spec.create_permission
            document = workflow_instance.document
            if permission and not user.has_perm(permission, document):
                raise exceptions.WorkflowCreateDenied(workflow_instance)

        @classmethod
        def can_cancel_course(cls, course_instance, user):
            """
            Verifies the user can cancel a course instance, given the instance and user.
            Both the workflow permission AND the course permission, if any, must be
              satisfied by the user.
            :param course_instance: The instance to check (will be already valid).
            :param user: The user to check
            :return: nothing
            """

            wf_permission = course_instance.course_spec.workflow_spec.cancel_permission
            cs_permission = course_instance.course_spec.cancel_permission
            document = course_instance.workflow_instance.document
            if wf_permission and not user.has_perm(wf_permission, document):
                raise exceptions.WorkflowCourseCancelDeniedByWorkflow(course_instance)
            if cs_permission and not user.has_perm(cs_permission, document):
                raise exceptions.WorkflowCourseCancelDeniedByCourse(course_instance)

        @classmethod
        def can_advance_course(cls, course_instance, transition, user):
            """
            Verifies the user can advance a course instance, given the instance and user.
            This check involves several cases:
            - The course instance is started and waiting on an Input node: the user
              satisfies the node's permission (if any) and the transition's permission
              (if any).
            - The course instance is starting and trying to execute the only transition
              from the only starting node: the user satisfies the transition's permission
              (if any).
            - The user is standing on a different node (not ENTER, not INPUT): this is
              always a failure. There will never be an allowance in this point.

            This method will be called when an explicit call to start or advance a
              workflow is performed. This means that multiplexer nodes or step nodes
              which are hit as intermediate steps of an execution will not call this
              method for their transitions.
            """

            document = course_instance.course_spec.workflow_spec
            try:
                node_instance = course_instance.node_instance
                # Reached this point, the node is either INPUT or a type we should not
                #   allow.
                if node_instance.node_spec.type != models.NodeSpec.INPUT:
                    raise exceptions.WorkflowCourseAdvanceDeniedByWrongNodeType(course_instance)
                else:
                    node_permission = node_instance.node_spec.execute_permission
                    if node_permission and not user.has_perm(node_permission, document):
                        raise exceptions.WorkflowCourseAdvanceDeniedByNode(course_instance)
                    transition_permission = transition.permission
                    if transition_permission and not user.has_perm(transition_permission, document):
                        raise exceptions.WorkflowCourseAdvanceDeniedByTransition(course_instance)
            except models.NodeInstance.DoesNotExist:
                # Reached this point, the workflow course was pending. It seems it is starting.
                # Right now the transition is the first transition, which has an ENTER node as its origin.
                transition_permission = transition.permission
                if transition_permission and not user.has_perm(transition_permission, document):
                    raise exceptions.WorkflowCourseAdvanceDeniedByTransition(course_instance)

    class CourseHelpers(object):
        """
        Helpers to get information from a course (instance or spec).
        """

        @classmethod
        def _check_status(cls, course_instance, types, invert=False):
            """
            Checks whether the instance's current node has a specific type or list of types.
              The condition can be inverted to see whether the instance's current node does
              not have that/those type(s). If the node does not exist, this method returns
              False. If the node does not exist AND the condition is requested to be inverted,
              this method returns True.
            :param course_instance: Instance to ask for.
            :param types: Node type or iterable with Node types to ask for.
            :param invert: Whether this condition is inverted or not.
            :return: Boolean indicating whether the course instance's node's type is among the
              given types.
            """

            try:
                return (course_instance.node_instance.node.type in iterable(types)) ^ bool(invert)
            except models.NodeInstance.DoesNotExist:
                return bool(invert)

        @classmethod
        def is_pending(cls, course_instance):
            return cls._check_status(course_instance, (), True)

        @classmethod
        def is_waiting(cls, course_instance):
            return cls._check_status(course_instance, models.NodeSpec.INPUT)

        @classmethod
        def is_cancelled(cls, course_instance):
            return cls._check_status(course_instance, models.NodeSpec.CANCEL)

        @classmethod
        def is_ended(cls, course_instance):
            return cls._check_status(course_instance, models.NodeSpec.EXIT)

        @classmethod
        def is_splitting(cls, course_instance):
            return cls._check_status(course_instance, models.NodeSpec.SPLIT)

        @classmethod
        def is_joined(cls, course_instance):
            return cls._check_status(course_instance, models.NodeSpec.JOINED)

        @classmethod
        def is_terminated(cls, course_instance):
            return cls._check_status(course_instance, (models.NodeSpec.JOINED, models.NodeSpec.EXIT,
                                                       models.NodeSpec.CANCEL))

        @classmethod
        def find_course(cls, course_instance, path):
            """
            Finds a specific course instance given a starting course instance and traversing the tree. The path
              will be broken by separating dot and the descendants will be searched until one course instance is
              found as described (by course codes) or an exception telling no element was found (or no element
              can be found) is triggered.
            :param course_instance: The course instance to check.
            :param path: The path to check under the course instance.
            :return: A descendant, or the same given, course instance.
            """

            if path == '':
                return course_instance
            elif not cls.is_splitting(course_instance):
                return exceptions.WorkflowNoSuchElement(course_instance, _('Course does not have children'))
            else:
                course_instance.verify_consistent_course()
                parts = path.split('.', 1)
                if len(parts) == 1:
                    head, tail = parts[0], ''
                else:
                    head, tail = parts
                try:
                    return cls.find_course(course_instance.node.branches.get(course__code=head), tail)
                except models.NodeInstance.DoesNotExist:
                    raise exceptions.WorkflowNoSuchElement(course_instance, _('Children course does not exist'), head)
                except models.NodeInstance.MultipleObjectsReturned:
                    raise exceptions.WorkflowNoSuchElement(course_instance, _('Multiple children courses exist '
                                                                              'with course code in path'), head)

    class WorkflowHelpers(object):
        """
        Helpers to get information from a node (instance or spec).
        """

        @classmethod
        def find_course(cls, workflow_instance, path):
            """
            Finds a specific course instance given a target workflow instance and traversing the tree. The path
              will be broken by separating dot and the descendants will be searched until one course instance is
              found as described (by course codes) or an exception telling no element was found (or no element
              can be found) is triggered.
            :param workflow_instance: The workflow instance to query.
            :param path: The path to check under the course instance.
            :return: A descendant, or the first (root), course instance.
            """

            workflow_instance.verify_exactly_one_parent_course()
            return Workflow.CourseHelpers.find_course(workflow_instance.courses.get(parent__isnull=True), path)

    class WorkflowRunner(object):

        @classmethod
        def _move(cls, course_instance, node, user):
            """
            Moves the course to a new node. Checks existence (if node code specified) or consistency
              (if node instance specified).
            :param course_instance: The course instance to move.
            :param node: The node instance or code to move this course instance.
            :param user: The user invoking the action that caused this movement.
            """

            if isinstance(node, string_types):
                try:
                    node_spec = course_instance.course_spec.node_specs.get(code=node)
                except models.NodeSpec.DoesNotExist:
                    raise exceptions.WorkflowCourseNodeDoesNotExist(course_instance, node)
            else:
                if node.course != course_instance.course_spec:
                    raise exceptions.WorkflowCourseInstanceDoesNotAllowForeignNodes(course_instance, node)
                node_spec = node

            # We run validations on node_spec.
            node_spec.clean()

            # Now we must run the callable, if any.
            handler = node_spec.landing_handler
            if handler:
                handler(course_instance.workflow_instance.document, user)

            # Nodes of type INPUT, EXIT, SPLIT, JOINED and CANCEL are not intermediate execution nodes but
            #   they end the advancement of a course (EXIT, JOINED and CANCEL do that permanently, while
            #   INPUT and SPLIT will continue by running other respective workflow calls).
            #
            # Nodes of type ENTER, MULTIPLEXER, and STEP are temporary and so they should not be saved like that.
            if node_spec.type in (models.NodeSpec.INPUT, models.NodeSpec.SPLIT, models.NodeSpec.EXIT,
                                  models.NodeSpec.CANCEL, models.NodeSpec.JOINED):
                try:
                    course_instance.node_instance.delete()
                except models.NodeInstance.DoesNotExist:
                    pass
                node_instance = models.NodeInstance.objects.create(course_instance=course_instance, node_spec=node_spec)
                # For split nodes, we also need to create the pending courses as branches.
                if node_spec.type == models.NodeSpec.SPLIT:
                    for branch in node_spec.branches.all():
                        node_instance.branches.create(workflow_instance=course_instance.workflow_instance,
                                                      course_spec=branch)

        @classmethod
        def _cancel(cls, course_instance, user, level=0):
            """
            Moves the course recursively (if this course has children) to a cancel node.
              For more information see the _move method in this class.
            :param course_instance: The course instance being cancelled.
            :param user: The user invoking the action leading to this call.
            :param level: The cancellation level. Not directly useful except as information for the
              user, later in the database.
            :return:
            """

            if Workflow.CourseHelpers.is_terminated(course_instance):
                return
            node_spec = course_instance.course_spec.verify_has_cancel_node()
            course_instance.clean()
            if Workflow.CourseHelpers.is_splitting(course_instance):
                next_level = level + 1
                for branch in course_instance.node_instance.branches.all():
                    cls._cancel(branch, user, next_level)
            cls._move(course_instance, node_spec, user)
            course_instance.term_level = level
            course_instance.save()

        @classmethod
        def _join(cls, course_instance, user, level=0):
            """
            Moves the course recursively (if this course has children) to a joined node.
              For more information see the _move method in this class.
            :param course_instance: The course instance being joined.
            :param user: The user invoking the action leading to this call.
            :param level: The joining level. Not directly useful except as information for the
              user, later in the database.
            :return:
            """

            if Workflow.CourseHelpers.is_terminated(course_instance):
                return
            node_spec = course_instance.course_spec.verify_has_joined_node()
            if not node_spec:
                raise exceptions.WorkflowCourseInstanceNotJoinable(course_instance, _('This course is not joinable'))
            course_instance.clean()
            if Workflow.CourseHelpers.is_splitting(course_instance):
                next_level = level + 1
                for branch in course_instance.node_instance.branches.all():
                    cls._join(branch, user, next_level)
            cls._move(course_instance, node_spec, user)
            course_instance.term_level = level
            course_instance.save()

        @classmethod
        def _run_transition(cls, course_instance, transition, user):
            """
            Runs a transition in a course instance. Many things are ensured already:
            - The course has a valid origin (one which can have outbounds).
            - The transition's origin is the course instance's current node instance's
              node spec.
            :param course_instance: The course instance to run the transition on.
            :param transition: The transition to execute.
            :param user: The user trying to run by this transition.
            :return:
            """

            ####
            # course_instance and transition are already clean by this point
            ####

            # Obtain and validate elements to interact with
            origin = transition.origin
            origin.full_clean()
            destination = transition.destination
            destination.full_clean()
            course_spec = course_instance.course_spec
            course_spec.full_clean()

            # Check if we have permission to do this
            Workflow.PermissionsChecker.can_advance_course(course_instance, transition, user)

            # We move to the destination node
            cls._move(course_instance, destination, user)

            # We must see what happens next.
            # ENTER, CANCEL and JOINED types are not valid destination types.
            # INPUT, SPLIT are types which expect user interaction and will not
            #   continue the execution.
            # While...
            #   STEP nodes will continue the execution from the only transition they have.
            #   EXIT nodes MAY continue the execution by exciting a parent joiner or completing
            #     parallel branches (if the parent SPLIT has no joiner and only one outbound).
            #   MULTIPLEXER nodes will continue from a picked transition, depending on which
            #     one satisfies the condition. It will be an error if no transition satisfies
            #     the multiplexer condition.
            if destination.type == models.NodeSpec.EXIT:
                pass
            elif destination.type == models.NodeSpec.STEP:
                pass
            elif destination.type == models.NodeSpec.MULTIPLEXER:
                pass
