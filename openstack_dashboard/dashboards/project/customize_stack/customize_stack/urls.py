from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.project.customize_stack.views \
    import IndexView


urlpatterns = patterns(
    '',
    url(r'^$', IndexView.as_view(), name='index'),
)
