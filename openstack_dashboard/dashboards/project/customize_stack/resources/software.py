
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class SoftwareConfig(resources.BaseResource):
    def __init__(self, request):
        super(SoftwareConfig, self).__init__(request)
        self.resource_type = 'OS::Heat::SoftwareConfig'
        self.properties = ['config']

class SoftwareDeployment(resources.BaseResource):
    def __init__(self, request):
        super(SoftwareDeployment, self).__init__(request)
        self.resource_type = 'OS::Heat::SoftwareDeployment'
        self.properties = ['config', 'server']