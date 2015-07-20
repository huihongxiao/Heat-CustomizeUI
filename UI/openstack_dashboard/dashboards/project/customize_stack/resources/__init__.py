
import logging
import six

from horizon import forms
from oslo_utils import strutils
from oslo_serialization import jsonutils

from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api

class BaseResource(object):

    def __init__(self, request):
        self.resource_type = None
        self.properties = None
        self.forms = forms
        self.request = request

    def generate_prop_fields(self, params):
        fields = {}
        if self.properties is None:
            self.properties = params.keys()
        for prop_name, prop_data in params.items():
            if prop_name not in self.properties:
                continue
            if hasattr(self, 'handle_prop'):
                handler = getattr(self, 'handle_prop')
                field = handler(prop_name, prop_data)
            else:
                field = self._handle_common_prop(prop_name, prop_data)

            if field:
                fields[prop_name] = field

        return fields

    def generate_res_data(self, data):
        ret = {'depends_on': None}
        for key, value in data.items():
            if hasattr(self, 'handle_resource'):
                handler = getattr(self, 'handle_resource')
                val = handler(key, value)
            else:
                val = value
            if val:
                ret[key] = val
        return ret

    def _handle_common_prop(self, prop_name, prop_data):
        prop_form = None
        field_args = {
            'initial': prop_data.get('Default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('Description', '')
        }

        prop_type = prop_data.get('Type', None)
        hidden = strutils.bool_from_string(prop_data.get('NoEcho', False))
        if hidden:
            field_args['widget'] = forms.PasswordInput()
        if 'AllowedValues' in prop_data:
            choices = map(lambda x: (x, x), prop_data['AllowedValues'])
            field_args['choices'] = choices
            prop_form = self.forms.ChoiceField
        if 'Default' in prop_data:
            field_args['initial'] = six.text_type(prop_data['Default'])
        if 'MinLength' in prop_data:
            field_args['min_length'] = int(prop_data['MinLength'])
            field_args['required'] = prop_data.get('MinLength', 0) > 0
        if 'MaxLength' in prop_data:
            field_args['max_length'] = int(prop_data['MaxLength'])

        if 'MinValue' in prop_data:
            field_args['min_value'] = int(prop_data['MinValue'])
        if 'MaxValue' in prop_data:
            field_args['max_value'] = int(prop_data['MaxValue'])

        if prop_form:
            field = prop_form(**field_args)
        elif prop_type in ('Number', 'Integer'):
            field = forms.IntegerField(**field_args)
        elif prop_type in ('Boolean', 'boolean'):
            field = forms.BooleanField(**field_args)
        else:
            field = forms.CharField(**field_args)
        return field

    @staticmethod
    def _populate_flavor_choices(request):
        return instance_utils.flavor_field_data(request, True)

    @staticmethod
    def _populate_image_choices(request):
        return image_utils.image_field_data(request, True)

    @staticmethod
    def _populate_network_choices(request):
        return instance_utils.network_field_data(request, True)

    @staticmethod
    def _populate_keypair_choices(request):
        return instance_utils.keypair_field_data(request, True)

    @staticmethod
    def _create_upload_form_attributes(prefix, input_type, name):
        attributes = {}
        attributes['class'] = 'switched'
        attributes['data-switch-on'] = prefix + 'source'
        attributes['data-' + prefix + 'source-' + input_type] = name
        return attributes

    def save_user_file(self, file):
        return project_api.save_user_file(self.request.user.id, file)
