import time # type: ignore
import ink_display
ink = ink_display.InkDisplay()

def show_calendar():
    current_time = time.localtime()
    year = current_time[0]
    month = current_time[1]
    day = current_time[2]
    if len(str(day)) == 1:
        day = "0" + str(day)
    if len(str(month)) == 1:
        month = "0" + str(month)
    today_str = f"{year}{month}{day}"
    print(today_str)

    bin_url = f"https://pubdz.paperol.cn/bin/万年历{today_str}.bin"

    ink.clear()
    try:
        print("显示万年历")
        res = ink.display_bin_url(bin_url)
        return True
    except Exception as e:
        print(f"显示万年历错误{e}")
        return False
    finally:
        ink.show()