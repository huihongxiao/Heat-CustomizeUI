
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
        self.properties = ['instance_uuid', 'mountpoint']
