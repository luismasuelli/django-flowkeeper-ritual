from django.core.exceptions import ValidationError
from arcanelab.ouroboros.executors import Workflow
from arcanelab.ouroboros.models import NodeSpec, TransitionSpec
from arcanelab.ouroboros.support import CallableReference
from .support import ValidationErrorWrappingTestCase


# TODO WARNING I MADE CHANGES TO THE WAY THE BRANCHES BEHAVE.
# TODO   AT MODEL LEVEL, COURSES DO NOT ALLOW UNREACHABLE NODES AND
# TODO   -IF BEING CHILDREN COURSES- DO NOT ALLOW AN AUTOMATIC PATH
# TODO   FROM THE ENTER NODE TO ANY EXIT NODE, WITHOUT NODES OF TYPE
# TODO   SPLIT OR INPUT. TESTS MUST BE CHANGED ACCORDINGLY SO THEY
# TODO   TEST THESE VALIDATIONS AND DO NOT FAIL THEM IN THE BRANCHES
# TODO   NOT BEING TESTED (ALSO, CERTAIN TESTS WILL CHANGE THE WAY
# TODO   THEY FAIL, SO AN INTENSIVE CHECK MUST BE DONE). THESE CHANGES
# TODO   IN THE TESTS MUST BE AMEND-COMMITTED


##########################################
# TransitionSpec tests
##########################################


class TransitionSpecTestCase(ValidationErrorWrappingTestCase):

    def _base_install_workflow_spec(self):
        """
        Installs a dummy workflow, having all the possible nodes in a
          main course, being ok.
        """

        spec = {'model': 'sample.Task', 'code': 'wfspec', 'name': 'Workflow Spec', 'create_permission': '',
                'cancel_permission': '',
                'courses': [{
                    'code': '', 'name': 'Main',
                    'nodes': [{
                        'type': NodeSpec.ENTER, 'code': 'origin', 'name': 'Origin',
                    }, {
                        'type': NodeSpec.INPUT, 'code': 'input', 'name': 'Input'
                    }, {
                        'type': NodeSpec.SPLIT, 'code': 'split', 'name': 'Split', 'branches': ['foo', 'bar'],
                    }, {
                        'type': NodeSpec.STEP, 'code': 'step', 'name': 'Step'
                    }, {
                        'type': NodeSpec.MULTIPLEXER, 'code': 'decision', 'name': 'Decision'
                    }, {
                        'type': NodeSpec.EXIT, 'code': 'exit-1', 'name': 'Exit 1', 'exit_value': 101,
                    }, {
                        'type': NodeSpec.EXIT, 'code': 'exit-2', 'name': 'Exit 2', 'exit_value': 102,
                    }, {
                        'type': NodeSpec.CANCEL, 'code': 'cancel', 'name': 'Cancel',
                    }],
                    'transitions': [{
                        'origin': 'origin', 'destination': 'input', 'name': 'Initial transition',
                    }, {
                        'origin': 'input', 'destination': 'split', 'name': 'User transition',
                        'action_name': 'do'
                    }, {
                        'origin': 'split', 'destination': 'step', 'name': 'Post-split transition',
                        'action_name': 'done'
                    }, {
                        'origin': 'step', 'destination': 'decision', 'name': 'Post-step transition',
                    }, {
                        'origin': 'decision', 'destination': 'exit-1', 'name': 'Choice A',
                        'priority': 0, 'condition': 'sample.support.dummy_condition_a'
                    }, {
                        'origin': 'decision', 'destination': 'exit-2', 'name': 'Choice B',
                        'priority': 1, 'condition': 'sample.support.dummy_condition_b'
                    }]
                }, {
                    'code': 'foo', 'name': 'Foo',
                    'nodes': [{
                        'type': NodeSpec.ENTER, 'code': 'origin', 'name': 'Origin',
                    }, {
                        'type': NodeSpec.INPUT, 'code': 'input', 'name': 'Input'
                    }, {
                        'type': NodeSpec.EXIT, 'code': 'exit', 'name': 'Exit', 'exit_value': 100,
                    }, {
                        'type': NodeSpec.CANCEL, 'code': 'cancel', 'name': 'Cancel',
                    }, {
                        'type': NodeSpec.JOINED, 'code': 'joined', 'name': 'Joined',
                    }],
                    'transitions': [{
                        'origin': 'origin', 'destination': 'input', 'name': 'Initial Transition',
                        'permission': 'sample.start_task',
                    }, {
                        'origin': 'input', 'destination': 'exit', 'name': 'Final Transition',
                        'action_name': 'end'
                    }]
                }, {
                    'code': 'bar', 'name': 'Bar',
                    'nodes': [{
                        'type': NodeSpec.ENTER, 'code': 'origin', 'name': 'Origin',
                    }, {
                        'type': NodeSpec.INPUT, 'code': 'input', 'name': 'Input'
                    }, {
                        'type': NodeSpec.EXIT, 'code': 'exit', 'name': 'Exit', 'exit_value': 100,
                    }, {
                        'type': NodeSpec.CANCEL, 'code': 'cancel', 'name': 'Cancel',
                    }, {
                        'type': NodeSpec.JOINED, 'code': 'joined', 'name': 'Joined',
                    }],
                    'transitions': [{
                        'origin': 'origin', 'destination': 'input', 'name': 'Initial Transition',
                        'permission': 'sample.start_task',
                    }, {
                        'origin': 'input', 'destination': 'exit', 'name': 'Final Transition',
                        'action_name': 'end'
                    }]
                }]}
        return Workflow.Spec.install(spec)

    def test_transition_starting_on_exit_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='').node_specs.get(code='exit-1'),
                destination=installed.course_specs.get(code='').node_specs.get(code='exit-2'),
                name='Bad Transition'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'origin')

    def test_transition_starting_on_joined_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='foo').node_specs.get(code='joined'),
                destination=installed.course_specs.get(code='foo').node_specs.get(code='exit'),
                name='Bad Transition'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'origin')

    def test_transition_starting_on_cancel_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='').node_specs.get(code='cancel'),
                destination=installed.course_specs.get(code='').node_specs.get(code='exit-1'),
                name='Bad Transition'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'origin')

    def test_transition_ending_on_enter_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='').node_specs.get(code='input'),
                destination=installed.course_specs.get(code='').node_specs.get(code='origin'),
                name='Bad Transition', action_name='bad-trans'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'destination')

    def test_transition_ending_on_joined_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='foo').node_specs.get(code='origin'),
                destination=installed.course_specs.get(code='foo').node_specs.get(code='joined'),
                name='Bad Transition'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'destination')

    def test_transition_ending_on_cancel_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            TransitionSpec.objects.create(
                origin=installed.course_specs.get(code='').node_specs.get(code='origin'),
                destination=installed.course_specs.get(code='').node_specs.get(code='cancel'),
                name='Bad Transition'
            ).full_clean()
        exc = self.unwrapValidationError(ar.exception, 'destination')

    def test_transition_from_origin_with_condition_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='origin').outbounds.first()
            transition.condition = CallableReference('sample.support.dummy_condition_a')
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'condition')

    def test_transition_from_origin_with_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='origin').outbounds.first()
            transition.priority = 0
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')

    def test_transition_from_origin_with_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='origin').outbounds.first()
            transition.action_name = 'baz'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_split_with_condition_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='split').outbounds.first()
            transition.condition = CallableReference('sample.support.dummy_condition_a')
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'condition')

    def test_transition_from_split_with_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='split').outbounds.first()
            transition.priority = 0
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')

    def test_transition_from_split_without_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='split').outbounds.first()
            transition.action_name = None
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_split_with_permission_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='split').outbounds.first()
            transition.permission = 'sample.create_task'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'permission')

    def test_transition_from_split_with_duplicate_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='split').outbounds.create(
                name='Dupe Transition',
                action_name='done',  # duplicate
                destination=installed.course_specs.get(code='').node_specs.get(code='exit-1')
            )
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_input_with_condition_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='input').outbounds.first()
            transition.condition = CallableReference('sample.support.dummy_condition_a')
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'condition')

    def test_transition_from_input_with_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='input').outbounds.first()
            transition.priority = 0
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')

    def test_transition_from_input_without_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='input').outbounds.first()
            transition.action_name = None
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_input_with_duplicate_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='input').outbounds.create(
                name='Dupe Transition',
                action_name='do',  # duplicate
                destination=installed.course_specs.get(code='').node_specs.get(code='exit-1')
            )
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_step_with_condition_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='step').outbounds.first()
            transition.condition = CallableReference('sample.support.dummy_condition_a')
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'condition')

    def test_transition_from_step_with_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='step').outbounds.first()
            transition.priority = 0
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')

    def test_transition_from_step_with_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='step').outbounds.first()
            transition.action_name = 'foo'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_step_with_permission_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='step').outbounds.first()
            transition.permission = 'sample.create_task'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'permission')

    def test_transition_from_multiplexer_without_condition_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='decision').outbounds.first()
            transition.condition = None
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'condition')

    def test_transition_from_multiplexer_without_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='decision').outbounds.first()
            transition.priority = None
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')

    def test_transition_from_multiplexer_with_action_name_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='decision').outbounds.first()
            transition.action_name = 'foo'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'action_name')

    def test_transition_from_multiplexer_with_permission_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='decision').outbounds.first()
            transition.permission = 'sample.create_task'
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'permission')

    def test_transition_from_multiplexer_with_duplicate_priority_is_bad(self):
        installed = self._base_install_workflow_spec().spec
        with self.assertRaises(ValidationError) as ar:
            transition = installed.course_specs.get(code='').node_specs.get(code='decision').outbounds.get(
                priority=0
            )
            transition.priority = 1
            transition.full_clean()
        exc = self.unwrapValidationError(ar.exception, 'priority')
