import json
import logging

from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa
from django.http import HttpResponse  # noqa

from oslo_utils import strutils
import six

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api


LOG = logging.getLogger(__name__)

class SelectResourceForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Select Resource Type')
        help_text = _('Select a resource type to add to  a template.')

    resource_type = forms.ChoiceField(label=_("Resource Type"),
                                    help_text=_("Select the type of resource to add"))
    resource_type_show = ["OS::Nova::Server", "OS::Cinder::Volume", "OS::Cinder::VolumeAttachment", "OS::Heat::SoftwareConfig", "OS::Heat::SoftwareDeployment"]

    def __init__(self, *args, **kwargs):
        self.next_view = kwargs.pop('next_view')
        super(SelectResourceForm, self).__init__(*args, **kwargs)
        self.fields['resource_type'].choices = (
                self.get_resource_type_choices(self.request))

    def get_resource_type_choices(self, request):
        resource_type_choices = [('', _("Select a resource type"))]
        for resource_type in self._get_resource_types(request):
            if (resource_type.resource_type in self.resource_type_show):
                resource_type_choices.append((resource_type.resource_type, resource_type.resource_type))
        return sorted(resource_type_choices, key=lambda item: item[0])

    def _get_resource_types(self, request):
        resource_types = []
        try:
            resource_types = api.heat.resource_types_list(request)
        except Exception:
            msg = _('Resource type could not be retrieved.')
            exceptions.handle(request, msg)
        return resource_types

    def _get_resource_type(self, request, resource_type):
        resource_properties = {}
        try:
            resource = api.heat.resource_type_generate_template(request, resource_type)
            resource_properties = resource['Parameters']
        except Exception:
            msg = _('Unable to retrieve details of resource type %(rt)s' % {'rt': resource_type})
            exceptions.handle(request, msg)
        return resource_properties


    def handle(self, request, data):
        kwargs = self._get_resource_type(self.request, data.get('resource_type'))
        kwargs['resource_type'] = data.get('resource_type') 
        # NOTE (gabriel): This is a bit of a hack, essentially rewriting this
        # request so that we can chain it as an input to the next view...
        # but hey, it totally works.
        request.method = 'GET'

        return self.next_view.as_view()(request, **kwargs)


class ModifyResourceForm(forms.SelfHandlingForm):
    param_prefix = ''

    parameters = forms.CharField(
        widget=forms.widgets.HiddenInput)
    resource_type = forms.CharField(
        widget=forms.widgets.HiddenInput)

    resource_name = forms.RegexField(
        max_length=255,
        label=_('Resource Name'),
        help_text=_('Name of the resource to create.'),
        regex=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
        error_messages={'invalid':
                        _('Name must start with a letter and may '
                          'only contain letters, numbers, underscores, '
                          'periods and hyphens.')})
    depends_on = forms.ChoiceField(label=_('Select the resource to depend on'),
                     required=False)

    properties_show = {
        "OS::Nova::Server": ['image', 'flavor', 'networks', 'user_data'],
        "OS::Cinder::Volume": ['size'],
        "OS::Cinder::VolumeAttachment": ['instance_uuid', 'mountpoint'],
        "OS::Heat::SoftwareConfig": ['config'],
        "OS::Heat::SoftwareDeployment": ['config', 'server']
    }

    class Meta(object):
        name = _('Modify Resource Properties')


    def __init__(self, *args, **kwargs):
        parameters = kwargs.pop('parameters')
#        self.next_view = kwargs.pop('next_view')
        super(ModifyResourceForm, self).__init__(*args, **kwargs)
        resource_names = project_api.get_resource_names(self.request)
        resource_name_choice = [("", "")]
        for resource_name in resource_names:
            resource_name_choice.append((resource_name, resource_name))
        self.fields['depends_on'].choices = (resource_name_choice)
        LOG.info('Original Resource Parameters %s' % parameters)
        self._build_parameter_fields(parameters)

    def _build_parameter_fields(self, params):
        filter_parameters = self.properties_show[params['resource_type']]
        params_in_order = sorted(params.items())
        for param_key, param in params_in_order:

            if param_key == 'resource_type':
                self.fields['resource_type'].initial = param
                continue
            if not param_key in filter_parameters:
                continue

            field = None
            field_key = self.param_prefix + param_key
            field_args = {
                'initial': param.get('Default', None),
                'label': param.get('Label', param_key),
                'help_text': param.get('Description', '')                
#                'required': param.get('Default', None) is Nione
            }
            param_type = param.get('Type', None)
            hidden = strutils.bool_from_string(param.get('NoEcho', 'false'))
            if 'CustomConstraint' in param:
                choices = self._populate_custom_choices(
                    param['CustomConstraint'])
                field_args['choices'] = choices
                field = forms.ChoiceField(**field_args)

            elif 'AllowedValues' in param:
                choices = map(lambda x: (x, x), param['AllowedValues'])
                field_args['choices'] = choices
                field = forms.ChoiceField(**field_args)

            elif param_type == 'Json' and 'Default' in param:
                field_args['initial'] = json.dumps(param['Default'])
                field = forms.CharField(**field_args)

            elif param_type in ('CommaDelimitedList', 'String', 'Json'):
                if 'MinLength' in param:
                    field_args['min_length'] = int(param['MinLength'])
                    field_args['required'] = param.get('MinLength', 0) > 0
                if 'MaxLength' in param:
                    field_args['max_length'] = int(param['MaxLength'])
                if hidden:
                    field_args['widget'] = forms.PasswordInput()
                field = forms.CharField(**field_args)

            elif param_type == 'Number':
                if 'MinValue' in param:
                    field_args['min_value'] = int(param['MinValue'])
                if 'MaxValue' in param:
                    field_args['max_value'] = int(param['MaxValue'])
                field = forms.IntegerField(**field_args)

            # heat-api currently returns the boolean type in lowercase
            # (see https://bugs.launchpad.net/heat/+bug/1361448)
            # so for better compatibility both are checked here
            elif param_type in ('Boolean', 'boolean'):
                field = forms.BooleanField(**field_args)

            if field:
                self.fields[field_key] = field

    def handle(self, request, data):
        data.pop('parameters')
        LOG.info('Finalized Resource Parameters %s' % data)
        if data['resource_type'] == 'OS::Nova::Server':
            data['networks'] = [{'network': data['networks']}]
        project_api.add_resource_to_draft(request, data)
        # NOTE (gabriel): This is a bit of a hack, essentially rewriting this
        # request so that we can chain it as an input to the next view...
        # but hey, it totally works.
#        request.method = 'GET'
#        return self.next_view.as_view()(request, resource_details = data)

        return True

class LaunchStackForm(forms.SelfHandlingForm):
    stack_name = forms.RegexField(
        max_length=255,
        label=_('Stack Name'),
        help_text=_('Name of the stack to create.'),
        regex=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
        error_messages={'invalid':
                        _('Name must start with a letter and may '
                          'only contain letters, numbers, underscores, '
                          'periods and hyphens.')})

    timeout_mins = forms.IntegerField(
        initial=60,
        label=_('Creation Timeout (minutes)'),
        help_text=_('Stack creation timeout in minutes.'))
    enable_rollback = forms.BooleanField(
        label=_('Rollback On Failure'),
        help_text=_('Enable rollback on create/update failure.'),
        required=False)

    class Meta(object):
        name = _('Modify Resource Properties')


    def handle(self, request, data):
        project_api.launch_stack(request, data.get('stack_name'), data.get('enable_rollback'), data.get('timeout_mins'))
        return True

class DeleteResourceForm(forms.SelfHandlingForm):
    class Meta(object):
        name = _('Modify Resource Properties')

    def __init__(self, *args, **kwargs):
        self.resource_name = kwargs.pop('resource_name')
        super(DeleteResourceForm, self).__init__(*args, **kwargs)

    def handle(self, request, data):
        project_api.del_resource_from_draft(request, self.resource_name)
        return True
