
import logging
import json

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class FloatingIP(resources.BaseResource):
    def __init__(self, request):
        super(FloatingIP, self).__init__(request)
        self.resource_type = 'OS::Neutron::FloatingIP'
        self.properties = ['fixed_ip_address', 'floating_ip_address',
                           'floating_network', 'port_id']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'port_id':
            choices = self.filter_resource(['OS::Neutron::Port'],
                                           include_empty=True)
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'floating_network':
            choices = self._populate_network_choices()
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


class FloatingIPAssociation(resources.BaseResource):
    def __init__(self, request):
        super(FloatingIPAssociation, self).__init__(request)
        self.resource_type = 'OS::Neutron::FloatingIPAssociation'

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'port_id':
            choices = self.filter_resource(['OS::Neutron::Port'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'floatingip_id':
            choices = self.filter_resource(['OS::Neutron::FloatingIP'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field

class Port(resources.BaseResource):
    def __init__(self, request):
        super(Port, self).__init__(request)
        self.resource_type = 'OS::Neutron::Port'
        self.properties = ['fixed_ips', 'network',
                           'security_groups']
        self.invisible_properties = ['subnet_id']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'network':
            choices = self._populate_network_choices()
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        # elif prop_name == 'subnet':
        #     choices = self._populate_network_choices()
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


class Subnet(resources.BaseResource):
    def __init__(self, request):
        super(Subnet, self).__init__(request)
        self.resource_type = 'OS::Neutron::Subnet'
        self.properties = ['cidr', 'dns_nameservers', 'enable_dhcp',
                           'gateway_ip', 'network', 'allocation_pools']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'network':
            choices = self._populate_network_choices(True)
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


class HealthMonitor(resources.BaseResource):
    def __init__(self, request):
        super(HealthMonitor, self).__init__(request)
        self.resource_type = 'OS::Neutron::HealthMonitor'


class LoadBalancer(resources.BaseResource):
    def __init__(self, request):
        super(LoadBalancer, self).__init__(request)
        self.resource_type = 'OS::Neutron::LoadBalancer'
        self.properties = ['pool_id', 'protocol_port']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'pool_id':
            choices = self.filter_resource(['OS::Neutron::Pool'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


class Pool(resources.BaseResource):
    def __init__(self, request):
        super(Pool, self).__init__(request)
        self.resource_type = 'OS::Neutron::Pool'
        self.properties = ['lb_method', 'protocol', 'subnet', 'monitors',
                           'vip']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'subnet':
            choices = self.filter_resource(['OS::Neutron::Subnet'])
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field


def resource_mapping():
    return {
        'OS::Neutron::FloatingIP': FloatingIP,
        'OS::Neutron::FloatingIPAssociation': FloatingIPAssociation,
        'OS::Neutron::Port': Port,
        'OS::Neutron::Subnet': Subnet,
        'OS::Neutron::HealthMonitor': HealthMonitor,
        'OS::Neutron::LoadBalancer': LoadBalancer,
        'OS::Neutron::Pool': Pool
    }