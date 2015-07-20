
import logging

from django.utils.translation import ugettext_lazy as _
from openstack_dashboard.dashboards.project.customize_stack import resources

class Resource(resources.BaseResource):
    def __init__(self, request):
        super(Resource, self).__init__(request)
        self.resource_type = 'OS::Nova::Server'
        self.properties = ['image', 'flavor', 'networks', 'key_name',
                           'user_data_format', 'user_data']

    def handle_prop(self, prop_name, prop_data):
        field_args = {
            'initial': prop_data.get('Default', None),
            'label': prop_data.get('Label', prop_name),
            'help_text': prop_data.get('Description', '')
        }
        if prop_name == 'flavor':
            choices = self._populate_flavor_choices(self.request)
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'image':
            choices = self._populate_image_choices(self.request)
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'key_name':
            choices = self._populate_keypair_choices(self.request)
            field_args['required'] = None
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
        elif prop_name == 'networks':
            choices = self._populate_network_choices(self.request)
            field_args['choices'] = choices
            field = self.forms.ChoiceField(**field_args)
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
        if name == 'networks':
            return [{'network': value}]
        elif name == 'user_data':
            files = self.request.FILES
            if files.get('user_data'):
                path = self.save_user_file(files.get('user_data'))
                return {'get_file': 'file://' + path}
            else:
                return None
        else:
            return value

def resource_mapping():
    return {
        'OS::Nova::Server': Resource
    }