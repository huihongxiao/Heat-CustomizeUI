
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class AutoScalingGroup(resources.BaseResource):
    def __init__(self, request):
        super(AutoScalingGroup, self).__init__(request)
        self.resource_type = 'OS::Heat::AutoScalingGroup'
        # self.properties = ['cooldown', 'max_size', 'min_size',
        #                    'resource', 'desired_capacity']
        # self.invisible_properties = [
        #     'resource', 'min_size', 'max_size',
        #     'desired_capacity', 'cooldown', 'desired_capacity',
        #     'rolling_updates',
        # ]

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'resource':
            attributes = self._create_upload_form_attributes(
                'resource',
                'file',
                _('Nested Template File'))
            field = self.forms.FileField(
                label=_('Nested Template File'),
                help_text=_('A template to upload.'),
                widget=self.forms.FileInput(attrs=attributes),
                required=True)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field

    def handle_resource(self, name, value):
        if name == 'resource':
            files = self.request.FILES
            if files.get('resource'):
                file_name = files.get('resource').name.encode('iso8859-1')
                return name, {'get_file': file_name}
            else:
                return None, None
        else:
            return name, value


class ScalingPolicy(resources.BaseResource):
    def __init__(self, request):
        super(ScalingPolicy, self).__init__(request)
        self.resource_type = 'OS::Heat::ScalingPolicy'

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'auto_scaling_group_id':
            choices = self.filter_resource(['OS::Heat::AutoScalingGroup'])
            field_args['choices'] = choices
            field_args['filter'] = 'OS::Heat::AutoScalingGroup'
            field = resources.FilterField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


def resource_mapping():
    return {
        'OS::Heat::AutoScalingGroup': AutoScalingGroup,
        'OS::Heat::ScalingPolicy': ScalingPolicy,
    }