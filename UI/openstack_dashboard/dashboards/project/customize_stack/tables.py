from collections import defaultdict
 
from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import defaultfilters as filters
from django.utils.http import urlencode
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
 
from horizon import tables
from horizon.utils.memoized import memoized  # noqa
 
from openstack_dashboard import api
from openstack_dashboard.api import base
 
from openstack_dashboard.dashboards.project.customize_stack \
    import api as project_api

class CreateTemplate(tables.LinkAction):
    name = "create"
    verbose_name = _("Create Template")
    url = "horizon:project:customize_stack:create_template"
    classes = ()
    icon = "plus"
    policy_rules = (("image", "add_image"),)
 
 
class EditTemplate(tables.LinkAction):
    name = "edit"
    verbose_name = _("Edit Template")
    url = "horizon:project:images:images:update"
    classes = ("ajax-modal",)
    icon = "pencil"
    policy_rules = (("image", "modify_image"),)
 
    def allowed(self, request, image=None):
#         if image:
#             return image.status in ("active",) and \
#                 image.owner == request.user.tenant_id
        # We don't have bulk editing, so if there isn't an image that's
        # authorized, don't allow the action.
        return True
 
class LaunchTemplate(tables.LinkAction):
    name = "launch_template"
    verbose_name = _("Launch Stack")
    url = "horizon:project:customize_stack:launch_template"
    classes = ("ajax-modal", "btn-launch")
    icon = "cloud-upload"
    policy_rules = (("compute", "compute:create"),)

    def get_link_url(self, datum):
        args = (datum.get('name'),)
        base_url = reverse(self.url, args=args)
        return base_url

    def allowed(self, request, image=None):
        return True

class DeleteTemplate(tables.DeleteAction):
    # NOTE: The bp/add-batchactions-help-text
    # will add appropriate help text to some batch/delete actions.
    help_text = _("Deleted templates are not recoverable.")

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Template",
            u"Delete Templates",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Template",
            u"Deleted Templates",
            count
        )

    policy_rules = (("image", "delete_image"),)

    def allowed(self, request, image=None):
        # Protected images can not be deleted.
#         if image and image.protected:
#             return False
#         if image:
#             return image.owner == request.user.tenant_id
        # Return True to allow table-level bulk delete action to appear.
        return True

    def delete(self, request, obj_id):
        project_api.delete_template(request, obj_id)

class OwnerFilter(tables.FixedFilterAction):
    def get_fixed_buttons(self):
        def make_dict(text, tenant, icon):
            return dict(text=text, value=tenant, icon=icon)

        buttons = [make_dict(_('Project'), 'project', 'fa-home')]
        for button_dict in filter_tenants():
            new_dict = button_dict.copy()
            new_dict['value'] = new_dict['tenant']
            buttons.append(new_dict)
        buttons.append(make_dict(_('Shared with Me'), 'shared',
                                 'fa-share-square-o'))
        buttons.append(make_dict(_('Public'), 'public', 'fa-group'))
        return buttons

#     def categorize(self, table, images):
#         user_tenant_id = table.request.user.tenant_id
#         tenants = defaultdict(list)
#         for im in images:
#             categories = get_image_categories(im, user_tenant_id)
#             for category in categories:
#                 tenants[category].append(im)
#         return tenants

def get_template_name(image):
    return getattr(image, "name", None) or image['name']
 
def get_template_type(image):
    return getattr(image, "properties", {}).get("image_type", "image")

def filter_tenants():
    return getattr(settings, 'IMAGES_LIST_FILTER_TENANTS', [])

@memoized
def filter_tenant_ids():
    return map(lambda ft: ft['tenant'], filter_tenants())

# def get_image_categories(im, user_tenant_id):
#     categories = []
#     if im.is_public:
#         categories.append('public')
#     if im.owner == user_tenant_id:
#         categories.append('project')
#     elif im.owner in filter_tenant_ids():
#         categories.append(im.owner)
#     elif not im.is_public:
#         categories.append('shared')
#     return categories

class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, image_id):
        pass
#     def load_cells(self, image=None):
#         super(UpdateRow, self).load_cells(image)
        # Tag the row with the image category for client-side filtering.
#         image = self.datum
#         my_tenant_id = self.table.request.user.tenant_id
#         image_categories = get_image_categories(image, my_tenant_id)
#         for category in image_categories:
#             self.classes.append('category-' + category)

class TemplatesTable(tables.DataTable):
#     STATUS_CHOICES = (
#         ("active", True),
#         ("saving", None),
#         ("queued", None),
#         ("pending_delete", None),
#         ("killed", False),
#         ("deleted", False),
#     )
#     STATUS_DISPLAY_CHOICES = (
#         ("active", pgettext_lazy("Current status of an Image", u"Active")),
#         ("saving", pgettext_lazy("Current status of an Image", u"Saving")),
#         ("queued", pgettext_lazy("Current status of an Image", u"Queued")),
#         ("pending_delete", pgettext_lazy("Current status of an Image",
#                                          u"Pending Delete")),
#         ("killed", pgettext_lazy("Current status of an Image", u"Killed")),
#         ("deleted", pgettext_lazy("Current status of an Image", u"Deleted")),
#     )
#     TYPE_CHOICES = (
#         ("image", pgettext_lazy("Type of an image", u"Image")),
#         ("snapshot", pgettext_lazy("Type of an image", u"Snapshot")),
#     )
    name = tables.Column(get_template_name,
                         link="horizon:project:customize_stack:edit_template",
                         verbose_name=_("Template Name"))
#     image_type = tables.Column(get_template_type,
#                                verbose_name=_("Type"),
#                                display_choices=TYPE_CHOICES)
#     status = tables.Column("status",
#                            verbose_name=_("Status"),
#                            status=True,
#                            status_choices=STATUS_CHOICES,
#                            display_choices=STATUS_DISPLAY_CHOICES)
#     public = tables.Column("is_public",
#                            verbose_name=_("Public"),
#                            empty_value=False,
#                            filters=(filters.yesno, filters.capfirst))
#     protected = tables.Column("protected",
#                               verbose_name=_("Protected"),
#                               empty_value=False,
#                               filters=(filters.yesno, filters.capfirst))
#     size = tables.Column("size",
#                          filters=(filters.filesizeformat,),
#                          attrs=({"data-type": "size"}),
#                          verbose_name=_("Size"))

    def get_object_id(self, datum):
        return datum['name']
    
    class Meta(object):
        name = "templates"
        row_class = UpdateRow
#         status_columns = ["status"]
        verbose_name = _("Stack Planning")
        table_actions = (CreateTemplate, DeleteTemplate,)
#         table_actions = ()
        launch_actions = ()
        launch_actions = (LaunchTemplate,) + launch_actions
        row_actions = launch_actions + (EditTemplate, DeleteTemplate,)
#         row_actions = ()
#         pagination_param = "image_marker"
