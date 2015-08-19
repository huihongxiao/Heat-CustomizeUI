
import json
import logging
import os
import pickle
import re
import threading
import six

from openstack_dashboard.api import heat
from openstack_dashboard.dashboards.project.stacks import mappings
from openstack_dashboard.dashboards.project.stacks import sro

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import messages


# file_path = "/etc/openstack-dashboard/cstack.data"
file_path = "/tmp/heat/%(user)s"

LOG = logging.getLogger(__name__)
# mutex = threading.Lock()

class Stack(object):
    pass

class Resource(object):
    pass

class Mutex(object):
    def __init__(self):
        self.locks = {}

    def acquire(self, user):
        if not self.locks.get(user):
            self.locks[user] = threading.Lock()
        return self.locks[user].acquire()

    def release(self, user):
        if not self.locks.get(user):
            self.locks[user] = threading.Lock()
        return self.locks[user].release()

mutex = Mutex()

def get_templates():
    templates = []
    dirname = '/tmp/heat/templates'
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    names = os.listdir(dirname)
    for name in names:
        template = {
            'name': name
        }
        templates.append(template)
    return templates;

def save_template(user, template_name):
    dirname = '/tmp/heat/templates'
    file_name = os.path.join(dirname, template_name)
    resources = _get_resources_from_file(user, None)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if mutex.acquire(user):
        f = open(file_name, 'wb')
        pickle.dump(resources, f)
        f.close()
        mutex.release(user)

def clean_template_folder(user, only_template=False):
    dirname = file_path % {'user': user}
    file_name = os.path.join(dirname, 'cstack.data')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if os.path.isfile(file_name):
        if mutex.acquire(user):
            LOG.info('Clear the draft template.')
            if not only_template:
                for f in [ff for ff in os.listdir(dirname)]:
                    os.remove(os.path.join(dirname, f))
            f = open(file_name, 'wb')
            pickle.dump([], f)
            f.close()
            mutex.release(user)

def _get_resources_from_file(user, template_name=None):
    if template_name is not None:
        dirname = '/tmp/heat/templates'
        file_name = os.path.join(dirname, template_name)
    else:
        dirname = file_path % {'user': user}
        file_name = os.path.join(dirname, 'cstack.data')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if os.path.isfile(file_name):
        if mutex.acquire(user):
            f = open(file_name, 'rb')
            resources = pickle.load(f)
#            LOG.info('Exsisting resources are %s' % resources)
            f.close()
            mutex.release(user)
    else:
        LOG.info('Could not find draft template file %s' % file_name)
        resources = []
    return resources


def _load_files_from_folder(user):
    dirname = file_path % {'user': user}
    ret = {}
    filelist = [os.path.join(dirname, ff)
                    for ff in os.listdir(dirname)
                    if ff != 'cstack.data']
    for ff in filelist:
        f = open(ff, 'r')
        content = f.read()
        f.close()
        ret['file://'+ff] = content
    return ret


def save_user_file(user, file):
    dirname = file_path % {'user': user}
    file_name = os.path.join(dirname, file.name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if mutex.acquire(user):
        f = open(file_name, 'wb')
        f.write(file.read())
        f.close()
        mutex.release(user)
    return file_name

def get_resource_names(request, template_name=None):
    resource_names = []
    resources = _get_resources_from_file(request.user.id, template_name)
    for resource in resources:
        resource_names.append(resource['resource_name'])
    return resource_names

def get_draft_template(request, template_name=None):
    resources = _get_resources_from_file(request.user.id, template_name)
    d3_data = {"nodes": []}

    if resources:
        for resource_folk in resources:
            resource = Resource()
            resource.resource_type = resource_folk['resource_type']
            resource.resource_name = resource_folk['resource_name']
            resource.required_by = [resource_folk['depends_on']]
            resource_image = mappings.get_resource_image(
                'COMPLETE',
                resource.resource_type)
            resource_node = {
                'name': resource.resource_name,
                'image': resource_image,
                'required_by': resource.required_by,
                'image_size': 50,
                'image_x': -25,
                'image_y': -25,
                'text_x': 35,
                'text_y': ".35em",
            }
            if 'parameters' in resource_folk:
                resource_folk.pop('parameters')
            resource_node['details'] = dict((key, six.text_type(value)) for key, value in resource_folk.items())
            d3_data['nodes'].append(resource_node)
    return json.dumps(d3_data)

def add_resource_to_draft(request, resource):
    dirname = file_path % {'user': request.user.id}
    file_name = os.path.join(dirname, 'cstack.data')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    resources = _get_resources_from_file(request.user.id)
    if mutex.acquire(request.user.id):
        f = open(file_name, 'wb')
        resources.append(resource)
        pickle.dump(resources, f)
        f.close()
        mutex.release(request.user.id)

def del_resource_from_draft(request, resource_name):
    dirname = file_path % {'user': request.user.id}
    file_name = os.path.join(dirname, 'cstack.data')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    resources = _get_resources_from_file(request.user.id)
    for idx, resource in enumerate(resources):
        if resource['resource_name'] == resource_name:
            resources.pop(idx)
            break
    del_dependencies(resources, resource_name)
    if mutex.acquire(request.user.id):
        f = open(file_name, 'wb')
        pickle.dump(resources, f)
        f.close()
        mutex.release(request.user.id)

def get_resourse_info(request, resource_name):
    resources = _get_resources_from_file(request.user.id)

    if resources:
        for resource_folk in resources:
            if resource_name == resource_folk['resource_name']:
                return resource_folk

def modify_resource_in_draft(request, modified, origin_name):
    dirname = file_path % {'user': request.user.id}
    file_name = os.path.join(dirname, 'cstack.data')
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    resources = _get_resources_from_file(request.user.id)
    to_modify = None
    for resource in resources:
        if resource['resource_name'] == origin_name:
            to_modify = resource
            break
    for key in modified:
        to_modify[key] = modified[key]
    if modified['resource_name'] != origin_name:
        modify_dependencies(resources, origin_name, modified['resource_name'])
    
    if mutex.acquire(request.user.id):
        f = open(file_name, 'wb')
        pickle.dump(resources, f)
        f.close()
        mutex.release(request.user.id)
        
def del_dependencies(resources, to_del):
    for resource in resources:
        if resource['depends_on'] == to_del:
            resource['depends_on'] = None
    
def modify_dependencies(resources, origin, new):
    for resource in resources:
        if resource['depends_on'] == origin:
            resource['depends_on'] = new
            
def _generate_template(resources):
    template = {
        'heat_template_version': '2013-05-23',
        'description': 'Generated by Heat UI.',
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
                try:
                    val = json.loads(value)
                except Exception:
                    val = value
                temp_res[res_name]['properties'][key] = val

    return json.loads(json.dumps(template))

def get_template_content(request, template_name=None):
    resources = _get_resources_from_file(request.user.id, template_name)
    template = _generate_template(resources)
    return json.dumps(template, indent=4)
    
    
def launch_stack(request, stack_name, enable_rollback, timeout):
    resources = _get_resources_from_file(request.user.id)
    template = _generate_template(resources)
    files = _load_files_from_folder(request.user.id)
    fields = {
            'stack_name': stack_name,
            'timeout_mins': timeout,
            'disable_rollback': not(enable_rollback),
            'password': None,
            'template': template,
            'files': files,
        }
    try:
        heat.stack_create(request, **fields)
        messages.success(request, _("Stack creation started."))
        clean_template_folder(request.user.id)
        return True
    except Exception:
        exceptions.handle(request)


def export_template(request):
    resources = _get_resources_from_file(request.user.id)
    template = _generate_template(resources)
    return json.dumps(template, indent=4)
