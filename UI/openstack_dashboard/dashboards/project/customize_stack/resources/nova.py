
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Server(resources.BaseResource):
    def __init__(self, request):
        super(Server, self).__init__(request)
        self.resource_type = 'OS::Nova::Server'
        self.invisible_properties = [
            'uuid', 'diskconfig', 'flavor_update_policy', 'reservation_id',
            'scheduler_hints', 'admin_user', 'admin_pass', 'block_device_mapping',
            'block_device_mapping_v2', 'image_update_policy', 'personality',
            'diskconfig',
        ]

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('description', ''),
            'required': prop_data.get('required', False)
        }
        if prop_name == 'flavor':
            choices = self._populate_flavor_choices()
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'image':
            choices = self._populate_image_choices()
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'key_name':
            choices = self._populate_keypair_choices()
            field_args['required'] = None
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'network':
            choices = (self._populate_network_choices() +
                       self.filter_resource(['OS::Neutron::Net']))
            field_args['choices'] = choices
            field_args['filter'] = 'OS::Neutron::Net'
            field = resources.FilterField(**field_args)
        elif prop_name == 'port':
            choices = self.filter_resource(['OS::Neutron::Port'], True)
            field_args['choices'] = choices
            field_args['filter'] = 'OS::Neutron::Port'
            field = resources.FilterField(**field_args)
        elif prop_name == 'availability_zone':
            choices = self._populate_availabilityzone_choices()
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'security_groups':
            choices = self._populate_secgroups_choices()
            field_args['choices'] = choices
            field_args['widget'] = self.forms.CheckboxSelectMultiple
            field = self.forms.MultipleChoiceField(**field_args)
        elif prop_name == 'user_data':
            attributes = self._create_upload_form_attributes(
                'user_data',
                'file',
                _('User Data File'))
            field = self.forms.FileField(
                label=_('User Data File'),
                help_text=_('A user data script to upload.'),
                widget=self.forms.FileInput(attrs=attributes),
                required=False)
        else:
            field = self._handle_common_prop(prop_name, prop_data)
        return field

    def handle_resource(self, name, value):
        if name == 'user_data':
            files = self.request.FILES
            if files.get('user_data'):
                file_name = files.get('user_data').name.encode('iso8859-1')
                return name, {'get_file': file_name}
#             elif self.data.get('user_data'):
#                 print value
#                 return name, value
            else:
                return None, None
        else:
            return name, value

def resource_mapping():
    return {
        'OS::Nova::Server': Server
    }