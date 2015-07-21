
import logging
import json

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Alarm(resources.BaseResource):
    def __init__(self, request):
        super(Alarm, self).__init__(request)
        self.resource_type = 'OS::Ceilometer::Alarm'
        self.properties = ['threshold ', 'alarm_actions', 'comparison_operator',
                           'evaluation_periods', 'insufficient_data_actions',
                           'meter_name', 'matching_metadata', 'ok_actions',
                           'period']

    def handle_resource(self, name, value):
        if name in ('alarm_actions', 'insufficient_data_actions',
                    'ok_actions'):
            ret = []
            data_list = value.split(',')
            for data in data_list:
                try:
                    val = json.loads(data)
                except Exception:
                    val = data
                ret.append(val)
            return name, ret
        else:
            return name, value


# class CombinationAlarm(resources.BaseResource):
#     def __init__(self, request):
#         super(CombinationAlarm, self).__init__(request)
#         self.resource_type = 'OS::Ceilometer::CombinationAlarm'
#         self.properties = ['operator', 'alarm_actions', 'alarm_ids',
#                            'insufficient_data_actions', 'ok_actions',
#                            'operator', 'repeat_actions']
#
#     def handle_resource(self, name, value):
#         if name in ('alarm_actions', 'insufficient_data_actions',
#                     'ok_actions'):
#             data_list = value.split(',')
#             return data_list
#         else:
#             return value


def resource_mapping():
    return {
        'OS::Ceilometer::Alarm': Alarm,
        # 'OS::Ceilometer::CombinationAlarm': CombinationAlarm
    }