
import logging
import six
import re

from horizon import forms
from oslo_utils import strutils
from oslo_serialization import jsonutils

from openstack_dashboard.dashboards.project.images \
    import utils as image_utils
from openstack_dashboard.dashboards.project.instances \
    import utils as instance_utils
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api
from openstack_dashboard import api
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _

from django.core.exceptions import ValidationError


class CharListItemField(forms.CharField):

    def to_python(self, value):
        if value in self.empty_values:
            return ''
        return value


class ListWidget(forms.MultiWidget):
    def __init__(self, widgets=None, attrs=None, labels=None):
        super(ListWidget, self).__init__(widgets, attrs)
        self.labels = labels

    def decompress(self, value):
        if value:
            return value
        return ''

    def format_output(self, rendered_widgets):
        ret = ''
        for i in range(len(rendered_widgets)):
            rendered = rendered_widgets[i]
            rendered = rendered.replace('class="', 'class="listItem ')
            if self.labels[i]:
                ret += ('<label>%s</label>%s' % (self.labels[i],
                                                 rendered))
            else:
                ret += '%s' % rendered
        
        r = re.compile('name="(.*)_\d"')
        m = r.search(ret)
        name = m.groups(1)[0]
        ret += '<a id="addItemButton" class="listWidgetButton btn btn-default" onclick="addListItem(\'' \
                + name + '\')"><span class="fa fa-plus"></span></a>'
        return ret

    def value_from_datadict(self, data, files, name):
        for i, widget in enumerate(self.widgets):
            print 'widget', widget
#         return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]
        values = []
        i = 0
        while True:
            itemName = name + '_%d' % i
            if itemName in data:
                values.append(data[itemName])
                i += 1
            else:
                break
        return [values]
    
class ListField(forms.MultiValueField):
    def __init__(self, fields=(), *args, **kwargs):
        super(ListField, self).__init__(*args, **kwargs)
        for f in fields:
            print 'field', f
            f.required = False
        self.fields = fields
        widgets = [ff.widget for ff in self.fields]
        self.labels = [ff.label for ff in self.fields]
        self.widget = ListWidget(widgets=widgets,
                                 labels=self.labels)

    def compress(self, data_list):
        print 'data_list', data_list
        if data_list:
            return [data for data in data_list if data and data != 'None']
        return []

    def bound_data(self, data, initial):
        return data

class MapField(forms.MultiValueField):
    def __init__(self, fields=(), *args, **kwargs):
        super(MapField, self).__init__(*args, **kwargs)
        for f in fields:
            f.required = False
        self.fields = fields
        widgets = [ff.widget for ff in self.fields]
        self.labels = [ff.label for ff in self.fields]
        self.widget = ListWidget(widgets=widgets,
                                 labels=self.labels)

    def compress(self, data_list):
        ret = {}
        if data_list:
            for i in range(len(data_list)):
                if data_list[i]:
                    ret[self.labels[i]] = data_list[i]
        return ret


class MapCharField(forms.CharField):
    default_error_messages = {
        'invalid': _('Enter a json format string.'),
    }

    def to_python(self, value):
        "Returns a Unicode object."
        if value in self.empty_values:
            return {}
        try:
            ret = jsonutils.loads(value.replace('\'', '\"'))
        except Exception as ex:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return ret



class BaseResource(object):

    def __init__(self, request):
        self.resource_type = None
        self.properties = None
        self.forms = forms
        self.request = request
        self.ListField = ListField
        self.invisible_properties = None

    def generate_prop_fields(self, params):
        fields = {}
        if self.properties is None:
            self.properties = params.keys()
        for prop_name, prop_data in sorted(params.items()):
            if prop_name not in self.properties:
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
            if val:
                ret[name] = val
        return ret

    def _handle_common_prop(self, prop_name, prop_data):
        prop_form = None
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
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
        if prop_form:
            field = prop_form(**field_args)
        elif prop_type in ('integer'):
            field = forms.IntegerField(**field_args)
        elif prop_type in ('number'):
            field = forms.FloatField(**field_args)
        elif prop_type in ('boolean'):
            field = forms.BooleanField(**field_args)
        elif prop_type in ('map'):
            fields = []
            schema = prop_data.get('schema', None)
            if schema:
                for name, data in sorted(schema.items()):
                    if (self.invisible_properties and
                                name in self.invisible_properties):
                        continue
                    if hasattr(self, 'handle_prop'):
                        handler = getattr(self, 'handle_prop')
                        ff = handler(name, data)
                    else:
                        ff = self._handle_common_prop(name, data)
                    fields.append(ff)
                field_args['fields'] = fields
                field = MapField(**field_args)
            else:
                field = MapCharField(**field_args)
        elif prop_type in ('list'):
            fields = []
            schema = prop_data.get('schema', None)
            if schema:
                fields.append(self._handle_common_prop('', schema['*']))
                field_args['fields'] = fields
            else:
                field_args['fields'] = [CharListItemField(label='')]
            field = ListField(**field_args)
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
