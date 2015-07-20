
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class SoftwareConfig(resources.BaseResource):
    def __init__(self, request):
        super(SoftwareConfig, self).__init__(request)
        self.resource_type = 'OS::Heat::SoftwareConfig'
        self.properties = ['config']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('Default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('Description', '')
        }
        if prop_name == 'config':
            attributes = self._create_upload_form_attributes(
                'config',
                'file',
                _('Script File'))
            field = self.forms.FileField(
                label=_('Script File'),
                help_text=_('A script to upload.'),
                widget=self.forms.FileInput(attrs=attributes),
                required=False)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field

    def handle_resource(self, name, value):
        if name == 'config':
            files = self.request.FILES
            if files.get('config'):
                path = self.save_user_file(files.get('config'))
                return {'get_file': 'file://' + path}
            else:
                return None
        else:
            return value

class SoftwareDeployment(resources.BaseResource):
    def __init__(self, request):
        super(SoftwareDeployment, self).__init__(request)
        self.resource_type = 'OS::Heat::SoftwareDeployment'
        self.properties = ['config', 'server']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('Default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('Description', '')
        }
        if prop_name == 'server':
            choices = self.filter_resource(['OS::Nova::Server'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'config':
            choices = self.filter_resource(['OS::Heat::SoftwareConfig'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


def resource_mapping():
    return {
        'OS::Heat::SoftwareConfig': SoftwareConfig,
        'OS::Heat::SoftwareDeployment': SoftwareDeployment,
    }
