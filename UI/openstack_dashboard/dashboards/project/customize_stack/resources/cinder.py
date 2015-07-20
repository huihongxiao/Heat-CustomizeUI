
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Volume(resources.BaseResource):
    def __init__(self, request):
        super(Volume, self).__init__(request)
        self.resource_type = 'OS::Cinder::Volume'
        self.properties = ['size']

class VolumeAttachment(resources.BaseResource):
    def __init__(self, request):
        super(VolumeAttachment, self).__init__(request)
        self.resource_type = 'OS::Cinder::VolumeAttachment'
        self.properties = ['instance_uuid', 'volume_id']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('Default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('Description', '')
        }
        if prop_name == 'instance_uuid':
            choices = self.filter_resource(['OS::Nova::Server'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'volume_id':
            choices = self.filter_resource(['OS::Cinder::Volume'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)

        return field
