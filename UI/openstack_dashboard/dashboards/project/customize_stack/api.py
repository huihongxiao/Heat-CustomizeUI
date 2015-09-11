
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

from django.forms import ValidationError  # noqa

# file_path = "/etc/openstack-dashboard/cstack.data"
# file_path = "/tmp/heat/%(user)s"
# dirname = '/tmp/heat/templates'

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

def validate_template_name(value):
    dirname = get_store_dir()
    names = os.listdir(dirname)
    valid = True
    for name in names:
        if (os.path.isdir(os.path.join(dirname, name))):
            if value == name:
                valid = False
                break
    if not valid:
        raise ValidationError('A template named as %s already exists.' % value)

def get_store_dir():
    store_dirname = '/tmp/heat/templates'
    if not os.path.exists(store_dirname):
        os.makedirs(store_dirname)
    return store_dirname

def get_template_dir(template_name):
    template_dirname = os.path.join(get_store_dir(), template_name)
    if not os.path.exists(template_dirname):
        os.makedirs(template_dirname)
    return template_dirname

def get_templates():
    templates = []
    dirname = get_store_dir()
    names = os.listdir(dirname)
    for name in names:
        if (os.path.isdir(os.path.join(dirname, name))):
            template = {
                'name': name
            }
            templates.append(template)
    return templates;

def save_template(template_name, canvas_data):
    file_name = os.path.join(get_template_dir(template_name), 'template')
    resources = json.loads(canvas_data)
    f = open(file_name, 'wb')
    pickle.dump(resources, f)
    f.close()

def delete_template(user, template_name):
    dir_name = get_template_dir(template_name)
    if mutex.acquire(user):
        for f in [ff for ff in os.listdir(dir_name)]:
            os.remove(os.path.join(dir_name, f))
        os.removedirs(dir_name)
        mutex.release(user)

def _get_resources_from_file(user, template_name=None):
    if not template_name:
        return []
    file_name = os.path.join(get_template_dir(template_name), 'template')
    if mutex.acquire(user):
        f = open(file_name, 'rb')
        resources = pickle.load(f)
        f.close()
        mutex.release(user)
    return resources

def _load_files_from_folder(template_name):
    dirname = get_template_dir(template_name)
    ret = {}
    for file_name in os.listdir(dirname):
        if file_name != 'template':
            file = open(os.path.join(dirname, file_name), 'r')
            content = file.read()
            file.close()
            ret[file_name] = content
    return ret


def save_user_file(template_name, files):
    dirname = get_template_dir(template_name)
    for file_name in files:
        file_path = os.path.join(dirname, file_name)
        file = open(file_path, 'wb')
        file.write(files[file_name].read())
        file.close()

def remove_useless_files(template_name, canvas_data):
    resources = json.loads(canvas_data)
    valid_files = []
    for resource in resources:
        for item in resource:
            if 'get_file' in resource[item]:
                eval(resource[item])
                valid_files.append(eval(resource[item])['get_file'])
    dirname = get_template_dir(template_name)
    names = os.listdir(dirname)
    for name in names:
        if not name in valid_files and name != 'template':
            os.remove(os.path.join(dirname, name))

def transfer_files(from_tml_name, to_tml_name):
    from_dir = get_template_dir(from_tml_name)
    to_dir = get_template_dir(to_tml_name)
    file_names = os.listdir(from_dir)
    for file_name in file_names:
        if file_name != 'template':
            from_path = os.path.join(from_dir, file_name)
            from_file = open(from_path, 'rb')
            to_path = os.path.join(to_dir, file_name)
            to_file = open(to_path, 'wb')
            to_file.write(from_file.read())
            from_file.close()
            to_file.close()
    
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

def gen_resource_d3_data(resource_folk):
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
    return resource_node

# def add_resource_to_draft(request, resource):
#     dirname = file_path % {'user': request.user.id}
#     file_name = os.path.join(dirname, 'cstack.data')
#     if not os.path.exists(dirname):
#         os.makedirs(dirname)
#     resources = _get_resources_from_file(request.user.id)
#     if mutex.acquire(request.user.id):
#         f = open(file_name, 'wb')
#         resources.append(resource)
#         pickle.dump(resources, f)
#         f.close()
#         mutex.release(request.user.id)

# def del_resource_from_draft(request, resource_name):
#     dirname = file_path % {'user': request.user.id}
#     file_name = os.path.join(dirname, 'cstack.data')
#     if not os.path.exists(dirname):
#         os.makedirs(dirname)
#     resources = _get_resources_from_file(request.user.id)
#     for idx, resource in enumerate(resources):
#         if resource['resource_name'] == resource_name:
#             resources.pop(idx)
#             break
#     del_dependencies(resources, resource_name)
#     if mutex.acquire(request.user.id):
#         f = open(file_name, 'wb')
#         pickle.dump(resources, f)
#         f.close()
#         mutex.release(request.user.id)

# def get_resourse_info(request, resource_name):
#     resources = _get_resources_from_file(request.user.id)
# 
#     if resources:
#         for resource_folk in resources:
#             if resource_name == resource_folk['resource_name']:
#                 return resource_folk
# 
# def modify_resource_in_draft(request, modified, origin_name):
#     dirname = file_path % {'user': request.user.id}
#     file_name = os.path.join(dirname, 'cstack.data')
#     if not os.path.exists(dirname):
#         os.makedirs(dirname)
#     resources = _get_resources_from_file(request.user.id)
#     to_modify = None
#     for resource in resources:
#         if resource['resource_name'] == origin_name:
#             to_modify = resource
#             break
#     for key in modified:
#         to_modify[key] = modified[key]
#     if modified['resource_name'] != origin_name:
#         modify_dependencies(resources, origin_name, modified['resource_name'])
#     
#     if mutex.acquire(request.user.id):
#         f = open(file_name, 'wb')
#         pickle.dump(resources, f)
#         f.close()
#         mutex.release(request.user.id)
        
# def del_dependencies(resources, to_del):
#     for resource in resources:
#         if resource['depends_on'] == to_del:
#             resource['depends_on'] = None
#     
# def modify_dependencies(resources, origin, new):
#     for resource in resources:
#         if resource['depends_on'] == origin:
#             resource['depends_on'] = new
#             
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
            if dependson != 'None':
                temp_res[res_name]['depends_on'] = dependson

        for key, value in resource.items():
            if value:
                try:
                    val = eval(value)
                except Exception:
                    val = value
                temp_res[res_name]['properties'][key] = val

    return json.loads(json.dumps(template))

def get_template_content(request, template_name=None):
    resources = _get_resources_from_file(request.user.id, template_name)
    template = _generate_template(resources)
    return json.dumps(template, indent=4)
    
    
def launch_draft(request, stack_name, enable_rollback, timeout, canvas_data):
    resources = json.loads(canvas_data)
    template = _generate_template(resources)
    files = _load_files_from_folder(request.user.id)
#     files = {}
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
        return True
    except Exception:
        exceptions.handle(request)
 
def launch_template(request, stack_name, enable_rollback, timeout, template_name):
    resources = _get_resources_from_file(request.user.id, template_name)
    template = _generate_template(resources)
    files = _load_files_from_folder(template_name)
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
        return True
    except Exception:
        exceptions.handle(request)

def export_template(request, template_name=None):
    resources = _get_resources_from_file(request.user.id, template_name)
    template = _generate_template(resources)
    return json.dumps(template, indent=4)
