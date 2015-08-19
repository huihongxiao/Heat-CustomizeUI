import logging

from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import messages
from horizon import tabs
from openstack_dashboard import api
from openstack_dashboard import policy

from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api

LOG = logging.getLogger(__name__)

class CanvasTab(tabs.Tab):
    name = _("Canvas")
    slug = "canvas"
    template_name = 'project/customize_stack/index.html'
    
    def get_context_data(self, request):
        if 'name' in self.tab_group.kwargs:
            name = self.tab_group.kwargs['name']
            return {'name': name}
        return {}

class ContentTab(tabs.Tab):
    name = _("Content")
    slug = "content"
    template_name = 'project/customize_stack/content.html'
    preload = False
    
    def get_context_data(self, request):
        try:
            if 'name' in self.tab_group.kwargs:
                content = project_api.get_template_content(request, self.tab_group.kwargs['name'])
            else:
                content = project_api.get_template_content(request)
        except Exception:
            msg = _('Unable to retrieve template contents.')
            exceptions.handle(request, msg)
            return None

        return {'content': content}

class CustomizeStackTabs(tabs.TabGroup):
    slug = "customizestack_tabs"
    tabs = (CanvasTab, ContentTab)