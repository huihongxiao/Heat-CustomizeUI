import json
import logging
from operator import attrgetter
import six

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
#        kwargs['next_view'] = PreviewResourceDetailsView
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

class ExporttemplateView(forms.ModalFormMixin, views.HorizonTemplateView):
    def get(self, request, **response_kwargs):
        data = project_api.export_template(request)
        response = HttpResponse(data, content_type='application/text')
        response['Content-Disposition'] = 'attachment; filename="example.template"'
        response['Content-Length'] = len(data.encode('utf8'))
        return response

class LaunchStackView(forms.ModalFormView):
    template_name = 'project/customize_stack/launch.html'
    modal_header = _("Launch Stack")
    form_id = "launch_stack"
    form_class = project_forms.LaunchStackForm
    submit_label = _("Launch")
    submit_url = reverse_lazy("horizon:project:customize_stack:launch_stack")
    success_url = reverse_lazy('horizon:project:stacks:index')
    page_title = _("Launch Stack")

class ClearCanvasView(forms.ModalFormView):
    template_name = 'project/customize_stack/clear.html'
    modal_header = _("Clear Canvas")
    form_id = "clear_canvas"
    form_class = project_forms.ClearCanvasForm
    submit_label = _("Confirm")
    submit_url = reverse_lazy("horizon:project:customize_stack:clear_canvas")
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Clear Canvas")

class JSONView(django.views.generic.View):
    def get(self, request):
        return HttpResponse(project_api.get_draft_template(request), content_type="application/json")

class DeleteResourceView(forms.ModalFormView):
    template_name = 'project/customize_stack/delete.html'
    modal_header = _("Delete Resource")
    form_id = "delete_resource"
    form_class = project_forms.DeleteResourceForm
    submit_label = _("Confirm")
    submit_url = "horizon:project:customize_stack:delete_resource"
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Delete Resource")


    def get_context_data(self, **kwargs):
        context = super(DeleteResourceView, self).get_context_data(**kwargs)
        args = (self.kwargs['resource_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_form_kwargs(self):
        kwargs = super(DeleteResourceView, self).get_form_kwargs()
        kwargs['resource_name'] = self.kwargs['resource_name']
        return kwargs
    

class EditResourceView(forms.ModalFormView):
    template_name = 'project/customize_stack/modify.html'
    modal_header = _("Edit Resource")
    form_id = "edit_resource"
    form_class = project_forms.ModifyResourceForm
    submit_label = _("Confirm")
    submit_url = "horizon:project:customize_stack:edit_resource"
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Edit Resource")
    
    def get_context_data(self, **kwargs):
        context = super(EditResourceView, self).get_context_data(**kwargs)
        args = (self.kwargs['resource_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def _get_resource_type(self, request, resource_type):
        resource_properties = {}
        try:
            # resource = api.heat.resource_type_generate_template(request, resource_type)
            # resource_properties = resource['Parameters']
            resource = api.heat.resource_type_get(request, resource_type)
            resource_properties = resource['properties']
        except Exception:
            msg = _('Unable to retrieve details of resource type %(rt)s' % {'rt': resource_type})
            exceptions.handle(request, msg)
        return resource_properties

    def _get_resource(self, resource_name):
#         resource_properties = {}
        resource = project_api.get_resourse_info(self.request, resource_name)
        return resource
    
    def get_initial(self):
        initial = {}
        resource = self._get_resource(self.kwargs['resource_name'])
        kwargs = self._get_resource_type(self.request, resource['resource_type'])
        kwargs['resource_type'] = resource['resource_type']
        # NOTE (gabriel): This is a bit of a hack, essentially rewriting this
        # request so that we can chain it as an input to the next view...
        # but hey, it totally works.
#         self.kwargs = kwargs
        
        initial['parameters'] = kwargs
        initial['resource'] = resource
        return initial

    def get_form_kwargs(self):
        kwargs = super(EditResourceView, self).get_form_kwargs()
#        kwargs['next_view'] = PreviewResourceDetailsView
        if not self.kwargs:
            kwargs['parameters'] = json.loads(self.request.POST['parameters'])
        else:
            kwargs['parameters'] = kwargs['initial']['parameters']
        kwargs['resource'] = kwargs['initial']['resource']
        return kwargs


class DynamicListView(forms.ModalFormView):
    template_name = 'project/customize_stack/additem.html'
    modal_header = _("Add Item")
    form_id = "add_item"
    form_class = project_forms.DynamicListForm
    submit_label = _("Add")
    submit_url = "horizon:project:customize_stack:add_item"
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Add Item")

    def get_object_id(self, obj):
        return obj

    def get_object_display(self, obj):
        return obj

    def get_context_data(self, **kwargs):
        context = super(DynamicListView, self).get_context_data(**kwargs)
        args = (self.kwargs['resource_type'], self.kwargs['property'])
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_form_kwargs(self):
        kwargs = super(DynamicListView, self).get_form_kwargs()
        kwargs['resource_type'] = self.kwargs['resource_type']
        kwargs['property'] = self.kwargs['property']
        return kwargs

    def get_form(self, form_class):
        """Returns an instance of the form to be used in this view."""
        return form_class(request=self.request, **self.get_form_kwargs())