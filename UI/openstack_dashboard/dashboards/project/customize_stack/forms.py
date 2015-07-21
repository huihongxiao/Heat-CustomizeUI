import json
import logging
import sys

from django.forms import ValidationError  # noqa
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa
from django.http import HttpResponse  # noqa

from oslo_utils import strutils

from horizon import exceptions
from horizon import forms
from horizon import messages

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api
from openstack_dashboard.dashboards.project.customize_stack.common \
    import plugin_loader
from openstack_dashboard.dashboards.project.customize_stack \
    import resources  #noqa


LOG = logging.getLogger(__name__)


def get_resource_mapping():
    ret = {}
    resources = sys.modules['openstack_dashboard.dashboards.project.customize_stack.resources']
    mods = list(plugin_loader.load_modules(resources))
    for mod in mods:
        if hasattr(mod, 'resource_mapping'):
            fun = getattr(mod, 'resource_mapping')
            res_map = fun()
            ret = dict(ret.items() + res_map.items())
    return ret

resource_type_map = get_resource_mapping()

def load_module(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

class SelectResourceForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Select Resource Type')
        help_text = _('Select a resource type to add to a template.')

    resource_type = forms.ChoiceField(label=_("Resource Type"),
                                    help_text=_("Select the type of resource to add"))

    def __init__(self, *args, **kwargs):
        self.next_view = kwargs.pop('next_view')
        super(SelectResourceForm, self).__init__(*args, **kwargs)
        self.fields['resource_type'].choices = (
                self.get_resource_type_choices(self.request))

    def get_resource_type_choices(self, request):
        resource_type_choices = [('', _("Select a resource type"))]
        for resource_type in self._get_resource_types(request):
            if resource_type.resource_type in resource_type_map.keys():
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
            # resource = api.heat.resource_type_generate_template(request, resource_type)
            # resource_properties = resource['Parameters']
            # import ipdb;ipdb.set_trace()
            resource = api.heat.resource_type_get(request, resource_type)
            resource_properties = resource['properties']
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

    origin_resource = None

    class Meta(object):
        name = _('Modify Resource Properties')

    def __init__(self, *args, **kwargs):
        parameters = kwargs.pop('parameters')
        resource = None
        if 'resource' in kwargs:
            resource = kwargs.pop('resource')
#        self.next_view = kwargs.pop('next_view')
        super(ModifyResourceForm, self).__init__(*args, **kwargs)
        self.is_multipart = True
        resource_names = project_api.get_resource_names(self.request)
        resource_name_choice = [("", "")]
        for resource_name in resource_names:
            resource_name_choice.append((resource_name, resource_name))
        if resource:
            for idx, choice in enumerate(resource_name_choice):
                if choice[0] == resource['resource_name']:
                    resource_name_choice.pop(idx)
                    break
            self.fields['depends_on'].initial = resource['depends_on']
            self.fields['resource_name'].initial = resource['resource_name']
            self.origin_resource = resource
        self.fields['depends_on'].choices = (resource_name_choice)
        LOG.info('Original Resource Parameters %s' % parameters)
        prop_type = parameters['resource_type']
        target_cls = resource_type_map.get(prop_type, None)
        self.res_cls = target_cls(self.request)
        self._build_parameter_fields(parameters, resource)

    def _build_parameter_fields(self, params, resource):
        if resource:
            for prop_name, prop_data in params.items():
                if prop_name in resource and isinstance(params[prop_name], dict):
                    params[prop_name]['Default'] = resource.get(prop_name)

        self.fields['resource_type'].initial = params.pop('resource_type')
        fields = self.res_cls.generate_prop_fields(params)
        for key, value in fields.items():
            self.fields[key] = value
    
    def clean(self, **kwargs):
        data = super(ModifyResourceForm, self).clean()

        existing_names = project_api.get_resource_names(self.request)
        if 'resource_name' in data:
            if self.origin_resource :
                for name in existing_names:
                    if data['resource_name'] == name and name != self.origin_resource['resource_name']:
                        raise ValidationError(
                            _("There is already a resource with the same name.")) 
            else :
                for name in existing_names:
                    if data['resource_name'] == name:
                        raise ValidationError(
                            _("There is already a resource with the same name.")) 
        return data

    def handle(self, request, data, **kwargs):
        data.pop('parameters')
        LOG.info('Finalized Resource Parameters %s' % data)
        res_data = self.res_cls.generate_res_data(data)
        if self.origin_resource:
            project_api.modify_resource_in_draft(self.request, res_data, self.origin_resource['resource_name'])
        else :
            project_api.add_resource_to_draft(self.request, res_data)
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

class ClearCanvasForm(forms.SelfHandlingForm):

    class Meta(object):
        name = _('Clear the canvas')

    def handle(self, request, data):
        project_api.clean_template_folder(self.request.user.id, only_template=True)
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
