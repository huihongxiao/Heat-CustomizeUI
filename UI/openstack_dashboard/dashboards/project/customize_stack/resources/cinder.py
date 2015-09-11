
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Volume(resources.BaseResource):
    def __init__(self, request):
        super(Volume, self).__init__(request)
        self.resource_type = 'OS::Cinder::Volume'
        self.invisible_properties = [
            'backup_id', 'description', 'imageRef', 'image',
            'source_volid', 'snapshot_id',
        ]

class VolumeAttachment(resources.BaseResource):
    def __init__(self, request):
        super(VolumeAttachment, self).__init__(request)
        self.resource_type = 'OS::Cinder::VolumeAttachment'

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'instance_uuid':
            choices = self.filter_resource(['OS::Nova::Server'])
            field_args['choices'] = choices
            field_args['filter'] = 'OS::Nova::Server'
            field = resources.FilterField(**field_args)
        elif prop_name == 'volume_id':
            choices = self.filter_resource(['OS::Cinder::Volume'])
            field_args['choices'] = choices
            field_args['filter'] = 'OS::Cinder::Volume'
            field = resources.FilterField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)

        return field


def resource_mapping():
    return {
        'OS::Cinder::Volume': Volume,
        'OS::Cinder::VolumeAttachment': VolumeAttachment,
    }