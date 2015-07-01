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
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api


LOG = logging.getLogger(__name__)

class IndexView(views.APIView):
    # A very simple class-based view...
    template_name = 'project/customize_stack/index.html'


    def __init__(self, *args, **kwargs):
        super(IndexView, self).__init__(*args, **kwargs)
        project_api.ini_draft_template_file()

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
        # Add data to the context here...
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

    def get_initial(self):
        initial = {}
        initial['parameters'] = json.dumps(self.kwargs)
        return initial

    def get_form_kwargs(self):
        kwargs = super(ModifyResourceView, self).get_form_kwargs()
        kwargs['next_view'] = PreviewResourceDetailsView
        if not self.kwargs:
            kwargs['parameters'] = json.loads(self.request.POST['parameters'])
        else:
            kwargs['parameters'] = self.kwargs
        return kwargs


class PreviewResourceDetailsView(forms.ModalFormMixin, views.HorizonTemplateView):
    template_name = 'project/customize_stack/preview_details.html'
    page_title = _("Preview Resource Details")

    def get_context_data(self, **kwargs):
        context = super(
            PreviewResourceDetailsView, self).get_context_data(**kwargs)
        LOG.error("Resource details are %s" % self.kwargs['resource_details'])
        context['resource_details'] = self.kwargs['resource_details']
        return context

class LaunchStackView(forms.ModalFormView):
    template_name = 'project/customize_stack/launch.html'
    modal_header = _("Launch Stack")
    form_id = "launch_stack"
    form_class = project_forms.LaunchStackForm
    submit_label = _("Launch")
    submit_url = reverse_lazy("horizon:project:customize_stack:launch_stack")
    success_url = reverse_lazy('horizon:project:stacks:index')
#    success_url = reverse_lazy('horizon:project:stacks:index')
    page_title = _("Launch Stack")

class JSONView(django.views.generic.View):
    def get(self, request):
        return HttpResponse(project_api.get_draft_template(), content_type="application/json")
