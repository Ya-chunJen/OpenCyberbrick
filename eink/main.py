import wifi
wifi.connect_wifi()

def start_webserver():
    # 启动 websocket 服务器
    import ink_websocket
    ink_websocket.start_websocket_server()

def start_8am_task():
    import ink_calendar
    import time
    # 每天8点执行任务，定时显示万年历。第一次上电的时候，也执行一次。
    ink_calendar.show_calendar()
    last_hour = -1
    while True:
        current_time = time.localtime()
        hour = current_time[3]
        # 如果是8点且上次不是8点
        if hour == 8 and last_hour != 8:
            print("上午8点，执行任务")
            ink_calendar.show_calendar()
        last_hour = hour
        # 每小时检查一次
        print("进入休眠。。。")
        time.sleep(60*10)  # 休眠10分钟
        
if __name__ == "__main__":
    start_webserver()
    # start_8am_task()

