from django.conf.urls import patterns
from django.conf.urls import url

from openstack_dashboard.dashboards.project.customize_stack import views


urlpatterns = patterns(
    '',
    url(r'^$', views.TableView.as_view(), name='index'),
    url(r'^create_template$', views.CreateTemplateView.as_view(), name='create_template'),
    url(r'^edit_template/(?P<template_name>[^/]+)/$', views.EditTemplateView.as_view(), name='edit_template'),
    url(r'^save_draft$', views.SaveDraftView.as_view(), name='save_draft'),
    url(r'^save_template/(?P<template_name>[^/]+)/$', views.SaveTemplateView.as_view(), name='save_template'),
    url(r'^save_template_as$', views.SaveTemplateAsView.as_view(), name='save_template_as'),
    url(r'^select_resource$', views.SelectResourceView.as_view(), name='select_resource'),
    url(r'^modify_resource$', views.ModifyResourceView.as_view(), name='modify_resource'),
    url(r'^edit_resource/(?P<resource_type>[^/]+)/$', views.EditResourceView.as_view(), name='edit_resource'),
#     url(r'^clear_canvas$', views.ClearCanvasView.as_view(), name='clear_canvas'),
    url(r'^get_draft_template_data$', views.JSONView.as_view(), name='draft_template_data'),
    url(r'^get_template_data/(?P<template_name>[^/]+)/$', views.JSONView.as_view(), name='template_data'),
    url(r'^launch_draft$', views.LaunchDraftView.as_view(), name='launch_draft'),
    url(r'^launch_template/(?P<template_name>[^/]+)/', views.LaunchTemplateView.as_view(), name='launch_template'),
#     url(r'^delete_resource$', views.DeleteResourceView.as_view(), name='delete_resource'),
    url(r'^export_template$', views.ExporttemplateView.as_view(), name='export_template'),
    url(r'^add_item/(?P<resource_type>[^/]+)/(?P<property>[^/]+)/$', views.DynamicListView.as_view(), name='add_item'),
    url(r'^edit_item/(?P<resource_type>[^/]+)/(?P<property>[^/]+)/$', views.EditDynamicListView.as_view(), name='edit_item'),
)
