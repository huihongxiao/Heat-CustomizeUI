import json
import logging
from operator import attrgetter
import six

import yaml

from django import http
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse  # noqa
from django.utils.translation import ugettext_lazy as _
import django.views.generic

from horizon import exceptions
from horizon import forms
from horizon.forms import views as forms_views
from horizon import tables
from horizon import tabs
from horizon.utils import memoized
from horizon import views
from openstack_dashboard import api
from openstack_dashboard.dashboards.project.customize_stack \
    import forms as project_forms
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api
from openstack_dashboard.dashboards.project.customize_stack \
    import tabs as project_tabs
from openstack_dashboard.dashboards.project.customize_stack \
    import tables as project_tables


LOG = logging.getLogger(__name__)

class TableView(tables.DataTableView):
    table_class = project_tables.TemplatesTable
    template_name = 'project/customize_stack/table.html'
    page_title = _("Templates")

    def has_prev_data(self, table):
        return getattr(self, "_prev_%s" % table.name, False)

    def has_more_data(self, table):
        return getattr(self, "_more_%s" % table.name, False)

    def get_data(self):
        marker = self.request.GET.get(
            project_tables.TemplatesTable._meta.pagination_param, None)
        try:
            templates = project_api.get_templates()
        except Exception:
            templates = []
            exceptions.handle(self.request, _("Unable to retrieve templates."))
        return templates

class CreateTemplateView(tabs.TabView):
    tab_group_class = project_tabs.CustomizeStackTabs
    template_name = 'project/customize_stack/tabs_group.html'
    page_title = _("Create template")

    def get_tabs(self, request, *args, **kwargs):
        return project_tabs.CustomizeStackTabs(request, **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:customize_stack:create_template')

class EditTemplateView(CreateTemplateView):
    page_title = _("Edit template: {{ template_name }}")

    def get_context_data(self, **kwargs):
        context = super(EditTemplateView, self).get_context_data(**kwargs)
        context["template_name"] = kwargs['template_name']
        return context

    def get_tabs(self, request, *args, **kwargs):
        return project_tabs.CustomizeStackTabs(request, name=self.kwargs['template_name'], **kwargs)
    
    @staticmethod
    def get_redirect_url():
        return reverse('horizon:project:customize_stack:edit_template')

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
        if not self.kwargs:
            kwargs['parameters'] = json.loads(self.request.POST['parameters'])
        else:
            kwargs['parameters'] = self.kwargs
        return kwargs

    def form_valid(self, form):
        try:
            handled = form.handle(self.request, form.cleaned_data)
        except Exception:
            handled = None
            exceptions.handle(self.request)
        if handled:
            response = http.HttpResponse(handled)
            response['X-Horizon-Valid'] = True;
            return response
        else:
            return self.form_invalid(form)
   
class EditResourceView(ModifyResourceView):
    template_name = 'project/customize_stack/modify.html'
    modal_header = _("Edit Resource")
    form_id = "edit_resource"
    form_class = project_forms.EditResourceForm
    submit_label = _("Confirm")
    submit_url = "horizon:project:customize_stack:edit_resource"
    page_title = _("Edit Resource")
    
    def get_context_data(self, **kwargs):
        context = super(EditResourceView, self).get_context_data(**kwargs)
        args = (self.kwargs['resource_type'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def _get_resource_properties(self, request, resource_type):
        resource_properties = {}
        try:
            resource = api.heat.resource_type_get(request, resource_type)
            resource_properties = resource['properties']
        except Exception:
            msg = _('Unable to retrieve details of resource type %(rt)s' % {'rt': resource_type})
            exceptions.handle(request, msg)
        return resource_properties
    
    def get_initial(self):
        initial = {}
        kwargs = self._get_resource_properties(self.request, self.kwargs['resource_type'])
        kwargs['resource_type'] = self.kwargs['resource_type']
        initial['parameters'] = kwargs
        return initial

    def get_form_kwargs(self):
        kwargs = super(EditResourceView, self).get_form_kwargs()
        if not self.kwargs:
            kwargs['parameters'] = json.loads(self.request.POST['parameters'])
        else:
            kwargs['parameters'] = kwargs['initial']['parameters']
        return kwargs

# class PreviewResourceDetailsView(forms.ModalFormMixin, views.HorizonTemplateView):
#     template_name = 'project/customize_stack/preview_details.html'
#     page_title = _("Preview Resource Details")
# 
#     def get_context_data(self, **kwargs):
#         context = super(
#             PreviewResourceDetailsView, self).get_context_data(**kwargs)
#         LOG.error("Resource details are %s" % self.kwargs['resource_details'])
#         context['resource_details'] = self.kwargs['resource_details']
#         return context

class ExportTemplateView(forms.ModalFormMixin, views.HorizonTemplateView):
    def get(self, request, **response_kwargs):
        data = project_api.export_template(request, self.kwargs['template_name'])
        response = HttpResponse(data, content_type='application/text')
        response['Content-Disposition'] = 'attachment; filename="example.template"'
        response['Content-Length'] = len(data.encode('utf8'))
        return response

class ExportDraftView(forms.ModalFormMixin, views.HorizonTemplateView):
    def get(self, request, **response_kwargs):
        data = project_api.export_template(request, self.kwargs['template_name'])
        response = HttpResponse(data, content_type='application/text')
        response['Content-Disposition'] = 'attachment; filename="example.template"'
        response['Content-Length'] = len(data.encode('utf8'))
    
    def get_context_data(self, **kwargs):
        context = super(LaunchTemplateView, self).get_context_data(**kwargs)
        args = (self.kwargs['template_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context
    

class LaunchDraftView(forms.ModalFormView):
    template_name = 'project/customize_stack/launch.html'
    modal_header = _("Launch Stack")
    form_id = "launch_draft"
    form_class = project_forms.LaunchDraftForm
    submit_label = _("Launch")
    submit_url = reverse_lazy("horizon:project:customize_stack:launch_draft")
    success_url = reverse_lazy('horizon:project:stacks:index')
    page_title = _("Launch Stack")

class LaunchTemplateView(LaunchDraftView):
    form_id = "launch_template"
    form_class = project_forms.LaunchTemplateForm
    submit_url = ("horizon:project:customize_stack:launch_template")
    
    def get_context_data(self, **kwargs):
        context = super(LaunchTemplateView, self).get_context_data(**kwargs)
        args = (self.kwargs['template_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context
    
    def get_form_kwargs(self):
        kwargs = super(LaunchTemplateView, self).get_form_kwargs()
        kwargs['template_name'] = self.kwargs['template_name']
        return kwargs

class SaveDraftView(forms.ModalFormView):
    template_name = 'project/customize_stack/save.html'
    modal_header = _("Save Template")
    form_id = "heat_save_draft"
    form_class = project_forms.SaveDraftForm
    submit_label = _("Save")
    submit_url = reverse_lazy("horizon:project:customize_stack:save_draft")
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Save Template")

class SaveTemplateView(forms.ModalFormView):
    template_name = 'project/customize_stack/save_confirmation.html'
    modal_header = _("Save Template")
    form_id = "heat_save_template"
    form_class = project_forms.SaveTemplateForm
    submit_label = _("Save")
    submit_url = "horizon:project:customize_stack:save_template"
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Save Template")
    
    def get_context_data(self, **kwargs):
        context = super(SaveTemplateView, self).get_context_data(**kwargs)
        args = (self.kwargs['template_name'],)
        context['submit_url'] = reverse(self.submit_url, args=args)
        return context

    def get_form_kwargs(self):
        kwargs = super(SaveTemplateView, self).get_form_kwargs()
        kwargs['template_name'] = self.kwargs['template_name']
        return kwargs

class SaveTemplateAsView(SaveTemplateView):
    template_name = 'project/customize_stack/save_as.html'
    modal_header = _("Save Template As")
    form_id = "heat_save_template_as"
    form_class = project_forms.SaveTemplateAsForm
    submit_label = _("Save")
    submit_url = ("horizon:project:customize_stack:save_template_as")
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Save Template As")

class JSONView(django.views.generic.View):
    template_name = None
    def get(self, request):
        if self.template_name is not None:
            return HttpResponse(project_api.get_draft_template(request, self.kwargs['template_name']), content_type="application/json")
        else:
            return HttpResponse(project_api.get_draft_template(request), content_type="application/json")
    
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        if 'template_name' in self.kwargs:
            self.template_name = kwargs.pop('template_name')
        return handler(request, *args, **kwargs)

# class DeleteResourceView(forms.ModalFormView):
#     template_name = 'project/customize_stack/delete.html'
#     modal_header = _("Delete Resource")
#     form_id = "delete_resource"
#     form_class = project_forms.DeleteResourceForm
#     submit_label = _("Confirm")
#     submit_url = "horizon:project:customize_stack:delete_resource"
#     success_url = reverse_lazy('horizon:project:customize_stack:index')
#     page_title = _("Delete Resource")
# 
#     def get_context_data(self, **kwargs):
#         context = super(DeleteResourceView, self).get_context_data(**kwargs)
#         args = (self.kwargs['resource_name'],)
#         context['submit_url'] = reverse(self.submit_url, args=args)
#         return context
# 
#     def get_form_kwargs(self):
#         kwargs = super(DeleteResourceView, self).get_form_kwargs()
#         kwargs['resource_name'] = self.kwargs['resource_name']
#         return kwargs

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
    
class EditDynamicListView(DynamicListView):
    modal_header = _("Edit Item")
    form_id = "edit_item"
    form_class = project_forms.EditDynamicListForm
    submit_label = _("Confirm")
    submit_url = "horizon:project:customize_stack:edit_item"
    success_url = reverse_lazy('horizon:project:customize_stack:index')
    page_title = _("Edit Item")

    def form_valid(self, form):
        response = super(EditDynamicListView, self).form_valid(form)
        
        handled = form.handle(self.request, form.cleaned_data)
        if handled:
            if forms_views.ADD_TO_FIELD_HEADER in self.request.META:
                if "HTTP_X_HORIZON_EDIT_OPTION_INDEX" in self.request.META:
                    option_idx = self.request.META["HTTP_X_HORIZON_EDIT_OPTION_INDEX"]
                    response["X-Horizon-Edit-Option-Index"] = option_idx
        
        return response