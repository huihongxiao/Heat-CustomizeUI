
from django.template.defaultfilters import title  # noqa
from django.template.loader import render_to_string

from horizon.utils import filters


def resource_info(resource):
    resource.resource_status_desc = title(
        filters.replace_underscores(resource.resource_status)
    )
    if resource.resource_status_reason:
        resource.resource_status_reason = title(
            filters.replace_underscores(resource.resource_status_reason)
        )
    context = {}
    context['resource'] = resource
    return render_to_string('project/customize_stack/_resource_info.html',
                            context)
