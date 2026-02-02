import network # type: ignore
import ujson # type: ignore
import time # type: ignore
import ntptime # type: ignore
from machine import RTC # type: ignore

def connect_wifi():
    wlan_sta = network.WLAN(network.STA_IF)
    wlan_sta.active(True)
    try:
        with open("wificonfig.json", 'r') as f:
            wificonfig = ujson.load(f)
    except:
        wificonfig = {"ssid": "xx", "password": "xxxxxxx"}

    wlan_sta.connect(wificonfig["ssid"],wificonfig["password"])

    for i in range(10):
        if wlan_sta.isconnected():
            sync_time()
            break
        else:
            time.sleep(1)
    print(f"WIFI信息: {wlan_sta.ifconfig()}")
    return wlan_sta.isconnected()

def sync_time(timezone=8, retry_count=10):
    for attempt in range(retry_count):
        try:
            # 同步NTP时间
            ntptime.host = 'ntp.aliyun.com'
            ntptime.settime()
            print("时间同步成功。")
            # 获取UTC时间
            current_time = time.localtime()
            # 转换为东八区时间
            timestamp = time.mktime(current_time)  # 转为时间戳
            timestamp += timezone * 3600  # 加8小时
            # 将东八区时间设置回RTC
            local_time = time.localtime(timestamp)
            # 更新RTC为东八区时间
            rtc = RTC()
            rtc.datetime((
                local_time[0],  # year
                local_time[1],  # month
                local_time[2],  # day
                local_time[6],  # weekday (0-6, Monday is 0)
                local_time[3],  # hour
                local_time[4],  # minute
                local_time[5],  # second
                0               # microsecond
            ))
            print("时间同步成功。当前时间: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                local_time[0], local_time[1], local_time[2],
                local_time[3], local_time[4], local_time[5]))
            return True
        except Exception as e:
            print(f"时间同步失败 (尝试 {attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2)  # 等待2秒后重试
    return False
