
import logging
import six

from horizon import forms
from horizon import exceptions
# from horizon.forms import fields
# from horizon.forms import widgets
from oslo_utils import strutils
from oslo_serialization import jsonutils

from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api
from openstack_dashboard import api
from django.utils.datastructures import MultiValueDict, MergeDict

from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core import urlresolvers
from django.utils.safestring import mark_safe

class DependancyField(forms.ChoiceField):

    def __init__(self, choices=(), required=True, widget=None, label=None,
                 initial=None, help_text='', *args, **kwargs):
        label=_('Select the resource to depend on')
        required=False
        super(DependancyField, self).__init__(required=required, widget=widget, label=label,
            initial=initial, help_text=help_text, *args, **kwargs)
   
    def valid_value(self, value):
        return True

class DynamicListWidget(forms.SelectMultiple):
    _data_add_url_attr = "data-add-item-url"
    
    def __init__(self, attrs=None, choices=()):
        attrs = {'class':'dynamic_listbox'}
        super(DynamicListWidget, self).__init__(attrs)
        # choices can be any iterable, but we may need to render this widget
        # multiple times. Thus, collapse it into a list so it can be consumed
        # more than once.
        self.choices = list(choices)
        
    def render(self, name, value, attrs=None, choices=()):
        add_item_url = self.get_add_item_url()
        if add_item_url is not None:
            self.attrs[self._data_add_url_attr] = add_item_url
        if value:
            self.choices = [(v,v) for v in value]
        return super(DynamicListWidget, self).render(name, None, attrs, choices)

    def get_add_item_url(self):
        if callable(self.add_item_link):
            return self.add_item_link()
        try:
            if self.add_item_link_args:
                return urlresolvers.reverse(self.add_item_link,
                                            args=self.add_item_link_args)
            else:
                return urlresolvers.reverse(self.add_item_link)
        except urlresolvers.NoReverseMatch:
            return self.add_item_link

class DynamicListField(forms.MultipleChoiceField):
    widget = DynamicListWidget

    def __init__(self,
                 add_item_link=None,
                 add_item_link_args=None,
                 *args,
                 **kwargs):
        super(DynamicListField, self).__init__(*args, **kwargs)
        self.widget.add_item_link = add_item_link
        self.widget.add_item_link_args = add_item_link_args

    def validate(self, value):
        if not value and value != []:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

    def to_python(self, value):
        ret = []
        if value in self.empty_values:
            return ret
        for item in value:
            try:
                val = jsonutils.loads(item)
                if val:
                    ret.append(val)
            except Exception as ex:
                if item:
                    ret.append(item.encode('iso8859-1'))
        return jsonutils.dumps(ret)
    

class BaseResource(object):

    def __init__(self, request):
        self.resource_type = None
        self.forms = forms
        self.request = request
#         self.ListField = ListField
        self.invisible_properties = []

    def generate_prop_fields(self, params):
        fields = {}
        for prop_name, prop_data in sorted(params.items()):
            if prop_name in self.invisible_properties:
                continue
            if hasattr(self, 'handle_prop'):
                handler = getattr(self, 'handle_prop')
                field = handler(prop_name, prop_data)
            else:
                field = self._handle_common_prop(prop_name, prop_data)

            if field:
                fields[prop_name] = field

        return fields

    def generate_res_data(self, data):
        ret = {'depends_on': None}
        for key, value in sorted(data.items()):
            if hasattr(self, 'handle_resource'):
                handler = getattr(self, 'handle_resource')
                name, val = handler(key, value)
            else:
                name = key
                val = value
            if val or val == False:
                ret[name] = val
        return ret

    def _handle_common_prop(self, prop_name, prop_data):
        prop_form = None
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }

        prop_type = prop_data.get('type', None)
        hidden = strutils.bool_from_string(prop_data.get('NoEcho', False))
        if hidden:
            field_args['widget'] = forms.PasswordInput()
        if 'constraints' in prop_data:
            cons = prop_data['constraints']
            for con in cons:
                if 'allowed_values' in con:
                    choices = map(lambda x: (x, x), con['allowed_values'])
                    field_args['choices'] = choices
                    prop_form = self.forms.ChoiceField
                if 'range' in con:
                    min_max = con['range']
                    if 'min' in min_max:
                        field_args['min_value'] = int(min_max['min'])
                        if field_args.get('initial') is None:
                            field_args['initial'] = field_args['min_value']
                    if 'max' in min_max:
                        field_args['max_value'] = int(min_max['max'])
                # if 'length' in con:
                #     min_max = con['length']
                #     if 'min' in min_max:
                #         field_args['min_length'] = int(min_max['min'])
                #         field_args['required'] = min_max.get('min', 0) > 0
                #     if 'max' in min_max:
                #         field_args['max_length'] = int(min_max['max'])
        if prop_type in ('list'):
            field_args['add_item_link'] = "horizon:project:customize_stack:add_item"
            field_args['add_item_link_args'] = (self.resource_type, prop_name)
            if field_args['initial']:
                field_args['choices'] = [
                    (jsonutils.dumps(item), jsonutils.dumps(item)) if isinstance(item, dict) else (item, item)
                    for item in field_args['initial']]
                field_args['initial'] = [item[0] for item in field_args['choices']]
            else:
                field_args['choices'] = []
            field = DynamicListField(**field_args)
        elif prop_form:
            field = prop_form(**field_args)
        elif prop_type in ('integer', 'number'):
            field = forms.IntegerField(**field_args)
        elif prop_type in ('number'):
            field = forms.FloatField(**field_args)
        elif prop_type in ('boolean'):
            field = forms.BooleanField(**field_args)
#         elif prop_type in ('map'):
#             fields = []
#             schema = prop_data.get('schema', None)
#             if schema:
#                 for name, data in sorted(schema.items()):
#                     if (name in self.invisible_properties):
#                         continue
#                     if hasattr(self, 'handle_prop'):
#                         handler = getattr(self, 'handle_prop')
#                         ff = handler(name, data)
#                     else:
#                         ff = self._handle_common_prop(name, data)
#                     fields.append(ff)
#                 field_args['fields'] = fields
#                 field = MapField(**field_args)
#             else:
#                 field = MapCharField(**field_args)
        else:
            field = forms.CharField(**field_args)
        return field

    def _populate_flavor_choices(self, include_empty=True):
        return instance_utils.flavor_field_data(self.request, include_empty)

    def _populate_image_choices(self, include_empty=True):
        return image_utils.image_field_data(self.request, include_empty)

    def _populate_network_choices(self, include_empty=True):
        return instance_utils.network_field_data(self.request, include_empty)

    def _populate_keypair_choices(self, include_empty=True):
        return instance_utils.keypair_field_data(self.request, include_empty)

    def _populate_availabilityzone_choices(self, include_empty=True):
        try:
            zones = api.nova.availability_zone_list(self.request)
        except Exception:
            zones = []
            exceptions.handle(self.request,
                              _('Unable to retrieve availability zones.'))

        zone_list = [(zone.zoneName, zone.zoneName)
                     for zone in zones if zone.zoneState['available']]
        zone_list.sort()
        if not zone_list:
            zone_list.insert(0, ("", _("No availability zones found")))
        elif len(zone_list) > 1:
            zone_list.insert(0, ("", _("Any Availability Zone")))
        return zone_list

    def _populate_secgroups_choices(self, include_empty=True):
        security_group_list = []
        try:
            groups = api.network.security_group_list(self.request)
            security_group_list = [(sg.name, sg.name) for sg in groups]
        except Exception:
            exceptions.handle(self.request,
                              _('Unable to retrieve list of security groups'))
        return security_group_list

    @staticmethod
    def _create_upload_form_attributes(prefix, input_type, name):
        attributes = {}
        attributes['class'] = 'switched'
        attributes['data-switch-on'] = prefix + 'source'
        attributes['data-' + prefix + 'source-' + input_type] = name
        return attributes

    def save_user_file(self, file):
        return project_api.save_user_file(self.request.user.id, file)

    def filter_resource(self, resource_types=None, include_empty=False):
        resources = project_api._get_resources_from_file(self.request.user.id)
        if resource_types is None:
            ret = [(jsonutils.dumps({"get_resource": res.get('resource_name')}), res.get('resource_name'))
                    for res in resources]
        else:
            ret = [(jsonutils.dumps({"get_resource": res.get('resource_name')}), res.get('resource_name'))
                    for res in resources if res.get('resource_type') in resource_types]
        if include_empty:
            return [('', "None"), ] + ret
        else:
            return ret
