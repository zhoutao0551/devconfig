#-*- coding:utf-8 -*-

from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.db.models import Q
from django.conf import settings
from xadmin.models import *
import random
import json


# "http://config.wifi-dog.com/get_config?mac=20:76:93:31:D1:28&id=9b558da3f6d2706d&model=NEWIFI-MINI&ver_sub=107"
def get_config(request):
    def get_client_ip(request):
        try:
            real_ip = request.META['HTTP_X_FORWARDED_FOR']
            regip = real_ip.split(",")[0]
        except:
            try:
                regip = request.META['REMOTE_ADDR']
            except:
                regip = ""
        return regip

    def write_log(c, mac, ip, s, v):
        dt = time.strftime("%A %Y-%m-%d %H:%M:%S", time.localtime())
        text = "%s C=%s MAC=%s IP=%s S=%s V=%s\n" % (dt, c, mac, ip, s, v)
        file = "%slog/%s.log" % (settings.USER_PATH, ip)
        if os.path.exists(file):
            with open(file, "r+") as f:
                first_line = f.readline()
                f.seek(0)
                f.truncate()
                f.writelines([first_line, text])
        else:
            with open(file, "w+") as f:
                f.write(text)
        print(text)

    def file_iterator(file_name, chunk_size=512):
        with open(file_name, "rb") as f:
            while True:
                content = f.read(chunk_size)
                if content:
                    yield content
                else:
                    break

    try:
        if request.method == 'GET':
            mac = request.GET.get('mac', '')
            sn = request.GET.get('id', '')
            model = request.GET.get('model', '')
            ver_sub = request.GET.get('ver_sub', '')
            if sn is not '' and mac is not '' and model is not '' and ver_sub is not '':
                try:
                    dev = Device.objects.get(dev_id=sn, dev_mac=mac)
                except Exception as e:
                    print("Get data error, data may be empty.")
                    primary_ips = ConfigFile.objects.filter(is_default=True)
                    slave_ips = ConfigFile.objects.filter(is_default=None)
                    if primary_ips and slave_ips:
                        for p in primary_ips:
                            server_ip = p.dir_name_ip
                            # server_ip = p['dir_name_ip']
                            ips = Device.objects.extra(
                                select={'devip': "inet_aton(dev_ip)", 'primary_server': server_ip},
                                order_by=['-devip']).values('dev_ip')[0:1]
                            print(ips)
                            if ips:
                                ip = ips[0]['dev_ip'].split('.')
                                pos2 = int(ip[2])
                                pos3 = int(ip[3])
                                if pos2 < 254:
                                    if pos3 < 254:
                                        ip = "172.16.%s.%s" % (ip[2], pos3 + 1)
                                    else:
                                        ip = "172.16.%s.%s" % (pos2 + 1, 3)
                                    server_ip = p
                                    break
                                else:
                                    continue
                            else:
                                ip = settings.FRIST_IP  # 起始IP
                                server_ip = p
                                break
                        else:
                            return HttpResponse(json.dumps({'err': 1002, 'info': 'No IP is available.'}))

                        #  随机取值
                        slave_ip = slave_ips[random.randint(0, len(slave_ips)-1)]

                        if not DevType.objects.filter(dev_type=model):
                            models = DevType(dev_type=model, desc="设备自注册型号")
                            models.save()
                        dev = Device(dev_id=sn, dev_mac=mac, primary_server=server_ip, slave_server=slave_ip,
                                        deadline=datetime.datetime.now() + datetime.timedelta(days=1), dev_ip=ip)
                        dev.save()
                    else:
                        return HttpResponse(json.dumps({'err': 1003, 'info': 'Not assigned to a suitable IP.'}))
                    # 查库确认写入成功
                    dev = Device.objects.get(dev_id=sn, dev_mac=mac)

                print(dev.primary_server)
                config_file = "%sdata/%s/%s.tar.gz" % (settings.USER_PATH, dev.primary_server, dev.dev_ip)
                # config_file = "%sdata\\%s\\%s.tar.gz" % (settings.USER_PATH, dev.primary_server, dev.dev_ip)
                if os.path.exists(config_file):
                    onlog = OnlineLog(dev=dev, mac=mac)
                    onlog.save()
                    write_log(get_client_ip(request), mac, dev.primary_server, dev.dev_ip, ver_sub)
                    response = StreamingHttpResponse(file_iterator(config_file))
                    response['Content-Type'] = 'application/octet-stream'
                    response['Content-Disposition'] = 'attachment;filename="{0}"'.format(
                        "%s.tar.gz" % dev.dev_ip)
                    return response
                else:
                    HttpResponse(json.dumps("{'err':1004, 'info':'Config file does not exist.'}"))
    except Exception as e:
        print(e)
    return HttpResponse(json.dumps("{'err':1001, 'info':'The parameter or request method is wrong.'}"))


# http://config.wifi-dog.com/get_devinfo?mac=20:76:93:31:D1:28&id=9b558da3f6d2706d&model=NEWIFI-MINI&ver_sub=107
def get_devinfo(request):
    info = "{'err':1001, 'info':'The parameter or request method is wrong.'}"
    try:
        if request.method == 'GET':
            mac = request.GET.get('mac', '')
            sn = request.GET.get('id', '')
            model = request.GET.get('model', '')
            ver_sub = request.GET.get('ver_sub', '')
            if sn is not '' and mac is not '' and model is not '' and ver_sub is not '':
                try:
                    dev = Device.objects.get(dev_id=sn, dev_mac=mac)
                    info = str(
                        {'err': 1000, 'primary_server': dev.primary_server, 'slave_server': dev.slave_server,
                         'deadline': dev.deadline.strftime('%A %Y-%m-%d %H:%M:%S')})
                except Exception as e:
                    info = {'err': 1002, 'info': 'No device found.'}
    except Exception as e:
        print(e)
    return HttpResponse(json.dumps(info))

