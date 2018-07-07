from __future__ import absolute_import
import xadmin
from .models import UserSettings, Log
from xadmin.layout import *

from django.utils.translation import ugettext_lazy as _, ugettext

# import xadmin
from xadmin import views
from .models import Device, UserProfile, DevType, OnlineLog, ConfigFile  # , DMLOG, DOLOG
from xadmin.layout import Main, TabHolder, Tab, Fieldset, Row, Col, AppendedText, Side
from xadmin.plugins.inline import Inline
from .plugins.batch import BatchChangeAction


class UserSettingsAdmin(object):
    model_icon = 'fa fa-cog'
    hidden_menu = True


xadmin.site.register(UserSettings, UserSettingsAdmin)


@xadmin.sites.register(views.BaseAdminView)
class BaseSetting(object):
    enable_themes = False  # 主题功能
    use_bootswatch = False  # 用户主题操作


@xadmin.sites.register(views.CommAdminView)
class GlobalSetting(object):
    site_title = "计费期限管理系统"  # 系统名称
    site_footer = "2018 xxx.com All Rights Reserved | 蜀ICP备 00000000号-00"  # 底部版权栏
    # menu_style = "accordion"  # 将菜单栏收起来
    # global_search_models = [Device,]
    global_models_icon = {
        Log: "fa fa-book",
        Device: "fa fa-laptop",
        DevType: "fa fa-tag",
        OnlineLog: "fa fa-flag"

    }
    global_add_models = []


@xadmin.sites.register(Log)
class LogAdmin(object):
    def link(self, instance):
        if instance.content_type and instance.object_id and instance.action_flag != 'delete':
            admin_url = self.get_admin_url(
                '%s_%s_change' % (instance.content_type.app_label, instance.content_type.model),
                instance.object_id)
            return "<a href='%s'>%s</a>" % (admin_url, _('修改'))
        else:
            return ''
    link.short_description = "管理"
    link.allow_tags = True
    link.is_column = True
    list_display_links = ("link",)

    show_bookmarks = False  # 关闭标签功能
    list_display = ('action_time', 'user', 'ip_addr', '__str__', 'remark', 'link')
    list_filter = ['user', 'action_time']
    search_fields = ['ip_addr', 'message']

    def has_add_permission(self):
        """ 取消后台添加功能 """
        return False

    def has_delete_permission(self):
        """ 取消后台删除功能 """
        return False


# @xadmin.site.unregister(User)
# admin.site.register(User, MyUserAdmin)
# @xadmin.site.unregister(UserProfile)
# @xadmin.sites.register(UserProfile)
# class UserProfileAdmin(object):
#     pass


@xadmin.sites.register(Device)
class DeviceAdmin(object):
    list_display = (
        "dev_id", "dev_mac", "dev_type", "dev_ip", "primary_server", "slave_server", "deadline",  # "vpn_server_ip",
        "note")  # 后台自定义显示列
    list_display_links = ("note",)  # 编辑 超链接
    ordering = ["deadline"]
    exclude = ['id']  # 后台自定义不显示字段
    list_editable = ["dev_ip", "primary_server", "slave_server", "deadline"]  # 后台直接在表上修改数据
    search_fields = ["dev_id", "dev_mac", "primary_server", "slave_server"]  # 定义后台搜索
    list_filter = ["deadline"]  # 过滤器
    # list_quick_filter = [{"field": "dev_id", "limit": 10}]

    # ordering = ['-click_nums']  # 后台自定义默认排序

    relfield_style = "fk-ajax"  # "fk-select"
    reversion_enable = True

    # actions = [BatchChangeAction, ]
    # batch_fields = ("dev_id", "dev_mac", "primary_server", "slave_server")

    refresh_times = (10, 20)  # 表定时刷新
    show_bookmarks = False  # 关闭标签功能

    list_export = ('xls', 'csv')  # 导出格式
    show_detail_fields = ["dev_id"]  # 显示关联字段详细信息

    date_hierarchy = 'deadline'  # 详细时间分层筛选


@xadmin.sites.register(DevType)
class DevTypeAdmin(object):
    list_display = ("dev_type", "create_time", "desc")  # 后台自定义显示列
    list_display_links = ("desc",)  # 编辑 超链接
    ordering = ["create_time"]
    exclude = ['id']  # 后台自定义不显示字段
    # list_editable = ["dev_type"]  # 后台直接在表上修改数据
    search_fields = ["dev_type", "desc"]  # 定义后台搜索
    list_filter = False  # ["dev_type", "desc"]  # 过滤器
    # list_quick_filter = [{"field": "dev_id", "limit": 10}]

    # ordering = ['-click_nums']  # 后台自定义默认排序

    relfield_style = "fk-select"  # "fk-ajax"
    reversion_enable = True

    # actions = [BatchChangeAction, ]
    # batch_fields = ("dev_id", "dev_mac", "primary_server", "slave_server")

    refresh_times = (10, 20)  # 表定时刷新
    show_bookmarks = False  # 关闭标签功能

    list_export = ('xls', 'csv')  # 导出格式
    show_detail_fields = ["dev_type"]  # 显示关联字段详细信息


@xadmin.sites.register(ConfigFile)
class ConfigFileAdmin(object):
    # dir_name_ip, create_time, is_default
    list_display = ("dir_name_ip", "create_time", "desc")  # 后台自定义显示列
    list_display_links = ("desc",)  # 编辑 超链接
    ordering = ["create_time"]
    exclude = ['id']  # 后台自定义不显示字段
    # list_editable = ["dev_type"]  # 后台直接在表上修改数据
    search_fields = ["dir_name_ip", "desc"]  # 定义后台搜索
    list_filter = False  # 过滤器

    relfield_style = "fk-ajax"  # "fk-ajax"
    reversion_enable = True
    refresh_times = (10, 20)  # 表定时刷新
    show_bookmarks = False  # 关闭标签功能

    list_export = ('xls', 'csv')  # 导出格式
    show_detail_fields = ["dir_name_ip"]  # 显示关联字段详细信息


@xadmin.sites.register(OnlineLog)
class OnlineLogAdmin(object):
    list_display = ("dev", "mac", "online_time", "desc")  # 后台自定义显示列
    # readonly_fields = ["dev", "online_time", "desc"]  # 只读字段
    list_display_links = ("id",)  # 编辑 超链接
    ordering = ["-online_time"]
    exclude = ['id']  # 后台自定义不显示字段
    search_fields = ["dev__dev_id", "mac"]  # 定义后台搜索
    list_filter = False  # 过滤器

    relfield_style = "fk-ajax"  # "fk-select"  # "fk-ajax"
    reversion_enable = True

    actions = [BatchChangeAction, ]

    show_bookmarks = False  # 关闭标签功能

    list_export = ('xls', 'csv')  # 导出格式
    show_detail_fields = ["desc"]  # 显示关联字段详细信息

    def has_add_permission(self):
        """ 取消后台添加功能 """
        return False

