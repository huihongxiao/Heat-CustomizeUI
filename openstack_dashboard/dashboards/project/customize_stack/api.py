
import json
import logging
import os
import pickle
import re

from openstack_dashboard.api import heat
from openstack_dashboard.dashboards.project.stacks import mappings
from openstack_dashboard.dashboards.project.stacks import sro

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import messages


file_path = "/etc/openstack-dashboard/cstack.data"
LOG = logging.getLogger(__name__)

class Stack(object):
    pass

class Resource(object):
    pass

def ini_draft_template_file():
    if os.path.isfile(file_path):
        LOG.error('Clear the draft template.')
        f = open(file_path, 'wb')
        pickle.dump([], f)
        f.close()

def _get_resources_from_file():
    if os.path.isfile(file_path):
        f = open(file_path, 'rb')
        resources = pickle.load(f)
        LOG.error('Exsisting resources are %s' % resources)
        f.close()
    else:
        LOG.error('Could not find draft template file %s' % file_path)
        resources = []
    return resources

def get_resource_names():
    resource_names = []
    resources = _get_resources_from_file()
    for resource in resources:
        resource_names.append(resource['resource_name'])
    return resource_names

def get_draft_template():
    resources = _get_resources_from_file()
    d3_data = {"nodes": [], "stack": {}}
    stack = Stack()
    stack.id = ""
    stack.stack_name = ""
    stack.stack_status = 'INIT'
    stack.stack_status_reason = ''
    stack_image = mappings.get_resource_image('INIT', 'stack')
    stack_node = {
            'stack_id': stack.id,
            'name': stack.stack_name,
            'status': stack.stack_status,
            'image': stack_image,
            'image_size': 60,
            'image_x': -30,
            'image_y': -30,
            'text_x': 40,
            'text_y': ".35em",
            'in_progress': False,
            'info_box': sro.stack_info(stack, stack_image)
    }
    d3_data['stack'] = stack_node

    if resources:
        for resource_folk in resources:
            resource = Resource()
            resource.resource_type = resource_folk['resource_type']
            resource.resource_status = 'INIT'
            resource.resource_status_reason = 'INIT'
            resource.resource_name = resource_folk['resource_name']
            resource.required_by = [resource_folk['depends_on']]
            resource_image = mappings.get_resource_image(
                resource.resource_status,
                resource.resource_type)
            in_progress = True
            resource_node = {
                'name': resource.resource_name,
                'status': resource.resource_status,
                'image': resource_image,
                'required_by': resource.required_by,
                'image_size': 50,
                'image_x': -25,
                'image_y': -25,
                'text_x': 35,
                'text_y': ".35em",
                'in_progress': in_progress,
                'info_box': sro.resource_info(resource)
            }
            d3_data['nodes'].append(resource_node)
    return json.dumps(d3_data)

def add_resource_to_draft(resource):
    resources = _get_resources_from_file()
    f = open(file_path, 'wb')
    resources.append(resource)
    pickle.dump(resources, f)
    f.close()

def del_resource_from_draft():
    pass


def _generate_template(resources):
    template = {
        'heat_template_version': '2013-05-23',
        'resources': {},
    }
    temp_res = template['resources']
    for resource in resources:
        res_name = resource.get('resource_name')
        del resource['resource_name']
        temp_res[res_name] = {}
        temp_res[res_name]['properties'] = {}

        res_type = resource.get('resource_type')
        del resource['resource_type']
        temp_res[res_name]['type'] = res_type

        dependson = resource.get('depends_on')
        if dependson:
            del resource['depends_on']
            temp_res[res_name]['depends_on'] = dependson

        for key, value in resource.items():
            if value:
                temp_res[res_name]['properties'][key] = value

    return json.loads(json.dumps(template))


def launch_stack(request, stack_name, enable_rollback, timeout):
    resources = _get_resources_from_file()
    template = _generate_template(resources)
    fields = {
            'stack_name': stack_name,
            'timeout_mins': timeout,
            'disable_rollback': not(enable_rollback),
            'password': None,
            'template_data': template
        }

    try:
        heat.stack_create(request, **fields)
        messages.success(request, _("Stack creation started."))
        return True
    except Exception:
        exceptions.handle(request)

