import json
import logging
import sys
import six

from django.forms import ValidationError  # noqa
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_variables  # noqa
from django.http import HttpResponse  # noqa

from oslo_utils import strutils
from oslo_serialization import jsonutils

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
        if resource_type == 'template_resource':
            return resource_properties
        try:
            resource = api.heat.resource_type_get(request, resource_type)
            resource_properties = resource['properties']
        except Exception:
            msg = _('Unable to retrieve details of resource type %(rt)s' % {'rt': resource_type})
            exceptions.handle(request, msg)
        return resource_properties

    def handle(self, request, data):
        kwargs = self._get_resource_type(self.request, data.get('resource_type'))
        kwargs['resource_type'] = data.get('resource_type') 
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
    depends_on = resources.DependancyField()

    class Meta(object):
        name = _('Modify Resource Properties')

    def __init__(self, *args, **kwargs):
        parameters = kwargs.pop('parameters')
        super(ModifyResourceForm, self).__init__(*args, **kwargs)
        self.is_multipart = True
        res_type = parameters['resource_type']
        target_cls = resource_type_map.get(res_type, None)
        self.res_cls = target_cls(self.request)
        self._build_parameter_fields(parameters)
        if res_type == 'template_resource' or res_type.endswith('.yaml'):
            self.fields['resource_type'] = resources.TemplateField()
            

    def _build_parameter_fields(self, params):
        self.fields['resource_type'].initial = params.pop('resource_type')
        fields = self.res_cls.generate_prop_fields(params)
        for key, value in fields.items():
            print key, value
            self.fields[key] = value

    def clean(self, **kwargs):
        data = super(ModifyResourceForm, self).clean(**kwargs)
        if json.loads(self.data.get('res_name_dup')):
            raise ValidationError(
                    _("There is already a resource with the same name.")) 
        return data
    
    def handle(self, request, data, **kwargs):
#         data.pop('parameters')
        print data
        res_data = self.res_cls.generate_res_data(data)
        print json.dumps(project_api.gen_resource_d3_data(res_data))
        return json.dumps(project_api.gen_resource_d3_data(res_data))

class EditResourceForm(ModifyResourceForm):
    original_name = forms.CharField(
        widget=forms.widgets.HiddenInput)

    class Meta(object):
        name = _('Edit Resource Properties')

    def handle(self, request, data, **kwargs):
        original_name = data.pop('original_name')
        files_names = json.loads(self.data['file_widget_content'])
        res_data = self.res_cls.generate_res_data(data)
        for widget in files_names:
            res_data[widget] = files_names[widget]
        d3_data = project_api.gen_resource_d3_data(res_data)
        d3_data['original_name'] = original_name
        return json.dumps(d3_data)

class LaunchDraftForm(forms.SelfHandlingForm):
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
        name = _('Launch Stack')

    def handle(self, request, data):
        project_api.launch_draft(request, data.get('stack_name'), data.get('enable_rollback'), data.get('timeout_mins'), self.data['canvas_data'])
        return True

class LaunchTemplateForm(LaunchDraftForm):
    def __init__(self, *args, **kwargs):
        self.template_name = kwargs.pop('template_name')
        super(LaunchTemplateForm, self).__init__(*args, **kwargs)
    
    def handle(self, request, data):
        project_api.launch_template(request, data.get('stack_name'), data.get('enable_rollback'), data.get('timeout_mins'), self.template_name)
        return True

class ContentForm(forms.SelfHandlingForm):
    template_name = forms.RegexField(
        max_length=255,
        label=_('Template Name'),
        help_text=_('Name of the template to save as.'),
        regex=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
        error_messages={'invalid':
                        _('Name must start with a letter and may '
                          'only contain letters, numbers, underscores, '
                          'periods and hyphens.')},
        validators=[project_api.validate_template_name])
    def handle(self, request, data):
        return True

class SaveDraftForm(forms.SelfHandlingForm):
    template_name = forms.RegexField(
        max_length=255,
        label=_('Template Name'),
        help_text=_('Name of the template to save as.'),
        regex=r"^[a-zA-Z][a-zA-Z0-9_.-]*$",
        error_messages={'invalid':
                        _('Name must start with a letter and may '
                          'only contain letters, numbers, underscores, '
                          'periods and hyphens.')},
        validators=[project_api.validate_template_name])

    def __init__(self, *args, **kwargs):
        super(SaveDraftForm, self).__init__(*args, **kwargs)
        self.is_multipart = True

    class Meta(object):
        name = _('Save Template')

    def handle(self, request, data):
        project_api.save_template(data.get('template_name'), self.data['canvas_data'])
        project_api.save_user_file(data.get('template_name'), request.FILES)
        return True

class SaveTemplateForm(forms.SelfHandlingForm):
    def __init__(self, *args, **kwargs):
        self.template_name = kwargs.pop('template_name')
        super(SaveTemplateForm, self).__init__(*args, **kwargs)
        self.is_multipart = True

    class Meta(object):
        name = _('Save Template')

    def handle(self, request, data):
        project_api.save_template(self.template_name, self.data['canvas_data'])
        project_api.save_user_file(self.template_name, request.FILES)
        project_api.remove_useless_files(self.template_name, self.data['canvas_data'])
        return True

class SaveTemplateAsForm(SaveDraftForm):
    def __init__(self, *args, **kwargs):
        self.template_name = kwargs.pop('template_name')
        super(SaveTemplateAsForm, self).__init__(*args, **kwargs)
    
    class Meta(object):
        name = _('Save As')
    
    def handle(self, request, data):
        super(SaveTemplateAsForm, self).handle(request, data)
        project_api.transfer_files(self.template_name, data.get('template_name'))
        project_api.remove_useless_files(self.template_name, self.data['canvas_data'])
        return True

class DynamicListForm(forms.SelfHandlingForm):
    class Meta(object):
        name = _('Add Item to Property')

    def _get_property_schema(self, request, resource_type, property):
        property_schema = {}
        try:
            resource = api.heat.resource_type_get(request, resource_type)
            property_schema = resource['properties'][property]
        except Exception:
            msg = _('Unable to retrieve details of resource type %(rt)s' % {'rt': resource_type})
            exceptions.handle(request, msg)
        return property_schema

    def __init__(self, *args, **kwargs):
        self.resource_type = kwargs.pop('resource_type')
        self.property = kwargs.pop('property')
        request = kwargs.get('request')
        super(DynamicListForm, self).__init__(*args, **kwargs)
        target_cls = resource_type_map.get(self.resource_type, None)
        self.res_cls = target_cls(request)
        self.prop_schema = self._get_property_schema(request, self.resource_type, self.property)
        schema = self.prop_schema.get('schema', None)
        if schema:
            print schema
            fields = self.res_cls.generate_prop_fields(schema['*']['schema'])
            for key, value in fields.items():
                self.fields[key] = value
        else:
            self.fields[self.property] = forms.CharField(label=self.property, required=False)

    def handle(self, request, data):
        dt = data.get(self.property, data)
        tt = {}
        if isinstance(dt, dict):
            for key, value in sorted(data.items()):
                if value or value == False:
                    try:
                        val = eval(value)
                    except Exception:
                        val = value
                    tt[key] = val
            return json.dumps(tt)
        else:
            return dt
        
class EditDynamicListForm(DynamicListForm):
    class Meta(object):
        name = _('Edit Item')