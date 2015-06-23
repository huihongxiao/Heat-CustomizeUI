from django.utils.translation import ugettext_lazy as _

import horizon
from openstack_dashboard.dashboards.project import dashboard

class Customize_Stack(horizon.Panel):
    name = _("Customize Stack")
    slug = "customize_stack"


dashboard.Project.register(Customize_Stack)
