from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.project.customize_stack import views


urlpatterns = patterns(
    '',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^select_resource$', views.SelectResourceView.as_view(), name='select_resource'),
    url(r'^modify_resource$', views.ModifyResourceView.as_view(), name='modify_resource'),
    url(r'^clear_canvas$', views.ClearCanvasView.as_view(), name='clear_canvas'),
    url(r'^get_draft_template_data$', views.JSONView.as_view(), name='draft_template_data'),
    url(r'^launch_stack$', views.LaunchStackView.as_view(), name='launch_stack'),
    url(r'^delete_resource/(?P<resource_name>[^/]+)/$', views.DeleteResourceView.as_view(), name='delete_resource'),
    url(r'^export_template$', views.ExporttemplateView.as_view(), name='export_template'),
    url(r'^edit_resource/(?P<resource_name>[^/]+)/$', views.EditResourceView.as_view(), name='edit_resource') 
)