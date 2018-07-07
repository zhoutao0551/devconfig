import os
import re
import json
import django
import hashlib
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _, ugettext
from django.urls.base import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.base import ModelBase
from django.utils.encoding import python_2_unicode_compatible, smart_text

from django.db.models.signals import post_migrate
from django.contrib.auth.models import Permission, AbstractUser

from django.core.exceptions import ValidationError

import datetime
import decimal
import time

from dateutil.relativedelta import relativedelta
from xadmin.util import quote

AUTH_USER_MODEL = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def add_view_permissions(sender, **kwargs):
    """
    This syncdb hooks takes care of adding a view permission too all our
    content types.
    """
    # for each of our content types
    for content_type in ContentType.objects.all():
        # build our permission slug
        codename = "view_%s" % content_type.model

        # if it doesn't exist..
        if not Permission.objects.filter(content_type=content_type, codename=codename):
            # add it
            Permission.objects.create(content_type=content_type,
                                      codename=codename,
                                      name="Can view %s" % content_type.name)
            # print "Added view permission for %s" % content_type.name

# check for all our view permissions after a syncdb
post_migrate.connect(add_view_permissions)


@python_2_unicode_compatible
class Bookmark(models.Model):
    title = models.CharField(_(u'Title'), max_length=128)
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_(u"user"), blank=True, null=True)
    url_name = models.CharField(_(u'Url Name'), max_length=64)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    query = models.CharField(_(u'Query String'), max_length=1000, blank=True)
    is_share = models.BooleanField(_(u'Is Shared'), default=False)

    @property
    def url(self):
        base_url = reverse(self.url_name)
        if self.query:
            base_url = base_url + '?' + self.query
        return base_url

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _(u'Bookmark')
        verbose_name_plural = _('Bookmarks')


class JSONEncoder(DjangoJSONEncoder):

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, ModelBase):
            return '%s.%s' % (o._meta.app_label, o._meta.model_name)
        else:
            try:
                return super(JSONEncoder, self).default(o)
            except Exception:
                return smart_text(o)


@python_2_unicode_compatible
class UserSettings(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_(u"user"))
    key = models.CharField(_('Settings Key'), max_length=256)
    value = models.TextField(_('Settings Content'))

    def json_value(self):
        return json.loads(self.value)

    def set_json(self, obj):
        self.value = json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)

    def __str__(self):
        return "%s %s" % (self.user, self.key)

    class Meta:
        verbose_name = _(u'User Setting')
        verbose_name_plural = _('User Settings')


@python_2_unicode_compatible
class UserWidget(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_(u"user"))
    page_id = models.CharField(_(u"Page"), max_length=256)
    widget_type = models.CharField(_(u"Widget Type"), max_length=50)
    value = models.TextField(_(u"Widget Params"))

    def get_value(self):
        value = json.loads(self.value)
        value['id'] = self.id
        value['type'] = self.widget_type
        return value

    def set_value(self, obj):
        self.value = json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)

    def save(self, *args, **kwargs):
        created = self.pk is None
        super(UserWidget, self).save(*args, **kwargs)
        if created:
            try:
                portal_pos = UserSettings.objects.get(
                    user=self.user, key="dashboard:%s:pos" % self.page_id)
                portal_pos.value = "%s,%s" % (self.pk, portal_pos.value) if portal_pos.value else self.pk
                portal_pos.save()
            except Exception:
                pass

    def __str__(self):
        return "%s %s widget" % (self.user, self.widget_type)

    class Meta:
        verbose_name = _(u'User Widget')
        verbose_name_plural = _('User Widgets')


class UserProfile(AbstractUser):
    gender = models.CharField(max_length=4, verbose_name=u"性别", choices=(("male", u"男"), ("female", u"女")), default="male")
    address = models.CharField(verbose_name=u"地址", max_length=128, null=True, blank=True)
    mobile = models.CharField(verbose_name=u"手机", max_length=11, null=True, blank=True)

    def my_property(self):
        return self.last_name + self.first_name
    my_property.short_description = u'姓名'
    full_name = property(my_property)

    class Meta:
        verbose_name = "管理员"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


@python_2_unicode_compatible
class Log(models.Model):
    action_time = models.DateTimeField(
        _('action time'),
        default=timezone.now,
        editable=False,
    )
    user = models.ForeignKey(
        AUTH_USER_MODEL,
        models.CASCADE,
        verbose_name=_('user'),
    )
    ip_addr = models.GenericIPAddressField(_('action ip'), blank=True, null=True)
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_('content type'),
        blank=True, null=True,
    )
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), max_length=200)
    action_flag = models.CharField(_('action flag'), max_length=32)
    message = models.TextField(_('change message'), blank=True)
    remark = models.TextField(u'备注', default=u"空", blank=True, null=True)

    class Meta:
        verbose_name = _('管理记录')
        verbose_name_plural = verbose_name
        ordering = ('-action_time',)

    def __repr__(self):
        return smart_text(self.action_time)

    def __str__(self):
        if self.action_flag == 'create':
            return ugettext('Added "%(object)s".') % {'object': self.object_repr}
        elif self.action_flag == 'change':
            return ugettext('Changed "%(object)s" - %(changes)s') % {
                'object': self.object_repr,
                'changes': self.message,
            }
        elif self.action_flag == 'delete' and self.object_repr:
            return ugettext('Deleted "%(object)s."') % {'object': self.object_repr}

        return self.message

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.content_type.get_object_for_this_type(pk=self.object_id)


@python_2_unicode_compatible
class DevType(models.Model):
    dev_type = models.CharField(u'型号', max_length=32, unique=True)  # 设备类型
    create_time = models.DateTimeField(u'创建日期', auto_now=True)  # 创建日期
    desc = models.TextField(u'备注', default=u"空", blank=True, null=True)

    def __str__(self):
        return self.dev_type

    class Meta:
        verbose_name = u"设备型号"
        verbose_name_plural = verbose_name


class generate_random():
    @staticmethod
    def time2_md5():
        h = hashlib.md5()
        t = str(time.time())
        h.update(t.encode(encoding='utf-8'))
        return h.hexdigest()


@python_2_unicode_compatible
class ConfigFile(models.Model):
    ip = [(x, x) for x in os.listdir(settings.USER_PATH + "data") if
     re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", x)]
    # file_path = models.FilePathField(u'路径', path=os.path.dirname(os.path.dirname(__file__)), unique=True)  # 脚本路径
    dir_name_ip = models.CharField(u'IP', max_length=32, choices=ip, unique=True)  # 配置路径
    create_time = models.DateTimeField(u'创建日期', auto_now=True)  # 创建日期
    is_default = models.NullBooleanField(u'默认配置', default=False)
    # random_str = models.NullBooleanField(u'默认配置', default=False)
    # random_str = models.CharField(u'随机值', max_length=32, unique=True, default=generate_random.time2_md5)
    # random_str = models.CharField(u'随机值', max_length=32, unique=True, default=generate_random.time2_md5,
    # widget=forms.HiddenInput())
    desc = models.TextField(u'备注', default=u"空", blank=True, null=True)

    def __str__(self):
        return self.dir_name_ip

    class Meta:
        verbose_name = u"配置文件"
        verbose_name_plural = verbose_name


def validate_mac_format(val):
    p = re.compile(r'^([A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}$')
    if p.match(val) is None:
        raise ValidationError(u"请输入合法的mac地址.")


def validate_segment_format(val):
    p = re.compile(r'^((2[0-4]\d|25[0-5]|[01]?\d\d?)\.){3}(2[0-4]\d|25[0-5]|[01]?\d\d?)$')
    if p.match(val) is None:
        raise ValidationError(u"请输入合法的地址.")


class generate_deadline():
    @staticmethod
    def datatime():
        return datetime.datetime.now() + relativedelta(months=+1)


@python_2_unicode_compatible
class Device(models.Model):
    dev_id = models.CharField(u'设备ID', max_length=64, unique=False)  # 设备ID
    dev_mac = models.CharField(u'设备MAC',
                               max_length=32,
                               unique=False,
                               help_text=_('请使用格式, AA:BB:CC:DD:EE:FF。'),
                               validators=[validate_mac_format])  # 设备MAC
    dev_type = models.ForeignKey(DevType, on_delete=models.CASCADE, verbose_name="型号", default=1)
    dev_ip = models.GenericIPAddressField('IP', default="172.16.0.3", unique=False)  # ip
    primary_server = models.ForeignKey(ConfigFile, on_delete=models.CASCADE, verbose_name=u'主Server', related_name='primary')  # 主server ip
    slave_server = models.ForeignKey(ConfigFile, on_delete=models.CASCADE, verbose_name=u'备用Server', related_name='slave', blank=True,  null=True)  # 从ip

    create_time = models.DateTimeField(u'创建日期', auto_now=True)  # 创建日期
    deadline = models.DateTimeField(u'使用截止', default=generate_deadline.datatime)  # 截至日期

    note = models.TextField(u'备注', default=u"空", blank=True, null=True)  # 备注u

    def __str__(self):
        return self.dev_id

    class Meta:
        verbose_name = u"VPN设备"
        verbose_name_plural = verbose_name


@python_2_unicode_compatible
class OnlineLog(models.Model):
    dev = models.ForeignKey(Device, on_delete=models.CASCADE, verbose_name="设备ID",)
    mac = models.CharField(u'设备Mac',
                               max_length=32,
                               # unique=True,
                               # help_text=_('请使用格式, AA:BB:CC:DD:EE:FF。'),
                               # validators=[validate_mac_format]
                           )
    online_time = models.DateTimeField(u'上线日期', auto_now=True)
    desc = models.TextField(u'备注', default=u"空", blank=True, null=True)

    def __str__(self):
        return str(self.dev)

    class Meta:
        verbose_name = u"设备上线记录"
        verbose_name_plural = verbose_name


