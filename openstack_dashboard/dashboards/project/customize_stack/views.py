import json
import logging
from operator import attrgetter

import yaml

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse  # noqa
from django.utils.translation import ugettext_lazy as _
import django.views.generic

from horizon import exceptions
from horizon import forms
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import views
from openstack_dashboard import api
from openstack_dashboard.dashboards.project.customize_stack \
    import forms as project_forms

LOG = logging.getLogger(__name__)

class IndexView(views.APIView):
    # A very simple class-based view...
    template_name = 'project/customize_stack/index.html'

    def get_data(self, request, context, *args, **kwargs):
        context = {}
        d3_data = {}
        stack = {
            'name': "customize stack",
            'image': "/static/dashboard/img/stack-green.svg",
            'image_size': 60,
            'image_x': -30,
            'image_y': -30,
            'text_x': 40,
            'text_y': ".35em",
            'info_box': "<img src=\"/static/dashboard/img/stack-green.svg\" width=\"35px\" height=\"35px\" />\n<div id=\"stack_info\">\n    <h3>customize stack</h3>\n    <p class=\"error\">Create your own stack</p>\n</div>\n<div class=\"clear\"></div>\n\n\n    \n\n"
        }
        d3_data['nodes'] = []
        d3_data['stack'] = stack
        context['d3_data'] = json.dumps(d3_data)
        return context

class SelectResourceView(forms.ModalFormView):
    template_name = 'project/customize_stack/select.html'
    modal_header = _("Select Resource Type")
    form_id = "select_resource"
    form_class = project_forms.SelectResourceForm
    submit_label = _("Next")
    submit_url = reverse_lazy("horizon:project:customize_stack:select_resource")
    success_url = reverse_lazy('horizon:project:customize_stack:modify_resource')
    page_title = _("Select Resource Type")

    def get_form_kwargs(self):
        kwargs = super(SelectResourceView, self).get_form_kwargs()
        kwargs['next_view'] = ModifyResourceView
        return kwargs    

class ModifyResourceView(forms.ModalFormView):
    template_name = 'project/customize_stack/modify.html'
    modal_header = _("Modify Resource Properties")
    form_id = "modify_resource"
    form_class = project_forms.ModifyResourceForm
    submit_label = _("Add")
    submit_url = reverse_lazy("horizon:project:customize_stack:modify_resource")
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Modify Resource Properties")

    def get_form_kwargs(self):
        kwargs = super(ModifyResourceView, self).get_form_kwargs()
        kwargs['parameters'] = self.kwargs
        return kwargs
