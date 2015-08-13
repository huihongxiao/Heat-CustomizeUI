
import logging
import json

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Alarm(resources.BaseResource):
    def __init__(self, request):
        super(Alarm, self).__init__(request)
        self.resource_type = 'OS::Ceilometer::Alarm'


class CombinationAlarm(resources.BaseResource):
    def __init__(self, request):
        super(CombinationAlarm, self).__init__(request)
        self.resource_type = 'OS::Ceilometer::CombinationAlarm'


def resource_mapping():
    return {
        'OS::Ceilometer::Alarm': Alarm,
        'OS::Ceilometer::CombinationAlarm': CombinationAlarm
    }