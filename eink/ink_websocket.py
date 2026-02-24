import network # type: ignore
import usocket as socket # type: ignore
import uselect as select # type: ignore
from time import sleep, ticks_ms # type: ignore
import gc
import ubinascii # type: ignore
import ujson # type: ignore
import machine # type: ignore
wlan_sta = network.WLAN(network.STA_IF)

def handle_websocket_command(message):
    """处理客户端命令"""
    try:
        cmd_json = ujson.loads(message)
        cmd_type = cmd_json["cmd_type"]
        if cmd_type == "control":    
            return ujson.dumps({"cmd_type":"control", "return_detail": "success"})
        elif cmd_type == "wifi":
            wificonfig = {"ssid": cmd_json["ssid"], "password": cmd_json["password"]}
            with open("wificonfig.json", 'w') as f:
                ujson.dump(wificonfig, f)
            sleep(3)
            machine.reset()
            return ujson.dumps({"cmd_type":"wifi","return_detail": "success"})
        elif cmd_type == "wifistatus":
            return ujson.dumps({"cmd_type":"wifistatus","sta_ip":str(wlan_sta.ifconfig()[0])})
        elif cmd_type == "binary_data_string":
            # 获取Base64编码的字符串数据
            base64_data = cmd_json.get("data", "")
            # 解码Base64数据
            binary_data = ubinascii.a2b_base64(base64_data)
            # 保存到文件
            with open("byte_array.bin", "wb") as f:
                f.write(binary_data)
            import ink_display
            ink = ink_display.InkDisplay()
            ink.clear()
            ink.display_bin_file()
            ink.show()
            return ujson.dumps({"cmd_type":"binary_data_string", "return_detail": "success", "bytes_received": len(binary_data)})
    except Exception as e:
        return ujson.dumps({"cmd_type":"error","return_detail": str(e)})

def handle_http_request(request_json):
    """处理HTTP请求"""
    print("结构化的HTTP请求数据",request_json)
    request_method = request_json.get("method")
    if request_method == "GET":
        print("处理GET请求")
        if request_json["path"] == "/":
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nAccess-Control-Allow-Origin: *\r\n\r\n'
            with open("ink_web_index.html", "r", encoding='utf-8') as f:
                content = f.read()
            return response + content
        elif request_json["path"] == "/wifistatus":
            response = 'HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\n\r\n' + f"WIFI网络IP地址: {wlan_sta.ifconfig()[0]}"
            return response
        else:
            response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\n404 Not Found'
            return response
    elif request_method == "POST":
        print("处理POST请求")
        import ink_display
        ink = ink_display.InkDisplay()
        ink.clear()
        ink.display_jsondata(request_json.get("body"))
        ink.show()
        response = 'HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\n\r\n' + "显示成功"
        return response

def parse_query_string(query_string: str) -> dict:
    """
    手动解析类似 a=1&b=2 的查询字符串。
    """
    params = {}
    pairs = query_string.split('&')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key] = value
        else:
            params[pair] = ''
    return params

def parse_http_request(raw_data: bytes) -> dict:
    """
    在 MicroPython 中解析 HTTP 请求数据并返回结构化字典。
    :param raw_data: 原始 HTTP 请求的字节数据
    :return: 结构化的字典(JSON兼容)
    """
    try:
        data_str = raw_data.decode('utf-8')
    except UnicodeDecodeError:
        raise ValueError("无法解码输入数据")

    lines = data_str.split('\r\n')

    if not lines:
        raise ValueError("无效的 HTTP 请求")

    # 解析第一行：方法、路径、版本
    request_line = lines[0].strip()
    parts = request_line.split(' ')
    if len(parts) != 3:
        raise ValueError("无效的请求行")
    method, full_path, http_version = parts

    # 提取路径和查询参数
    path = full_path
    query_params = {}
    if '?' in full_path:
        path, query_string = full_path.split('?', 1)
        query_params = parse_query_string(query_string)

    # 解析 headers
    headers = {}
    body_start_index = 0
    for i in range(1, len(lines)):
        line = lines[i]
        if line == '':
            body_start_index = i + 1
            break
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    
    # 解析body（如果有）
    body = ""
    if body_start_index < len(lines):
        body_lines = lines[body_start_index:]
        body = '\r\n'.join(body_lines)
        
        # 如果是application/json类型，尝试解析JSON
        content_type = headers.get('Content-Type', '')
        if 'application/json' in content_type and body: # type: ignore
            try:
                body = ujson.loads(body)
            except:
                pass  # 如果解析失败，保持原始字符串
        
        # 如果是application/x-www-form-urlencoded类型，解析表单数据
        elif 'application/x-www-form-urlencoded' in content_type and body:
            try:
                body = parse_query_string(body)
            except:
                pass  # 如果解析失败，保持原始字符串

    result = {
        "method": method,
        "path": path,
        "query_params": query_params,
        "http_version": http_version,
        "headers": headers,
        "body": body
    }
    return result

def ws_handshake(sock, data):
    """处理WebSocket握手"""
    if b'Sec-WebSocket-Key:' in data:
        lines = data.decode().split('\r\n')
        key = None
        for line in lines:
            if line.startswith('Sec-WebSocket-Key:'):
                key = line.split(': ')[1]
                break
        
        if key:
            import uhashlib # type: ignore
            magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_key = ubinascii.b2a_base64(uhashlib.sha1((key + magic).encode()).digest()).decode().strip()
            
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: " + accept_key + "\r\n\r\n"
            )
            sock.send(response.encode())
            return True
    return False

def ws_receive(data):
    """解析WebSocket消息"""
    # 检查是否是握手响应（包含HTTP头）
    if b'\r\n\r\n' in data:
        # print("检测到握手响应，跳过...")
        header_end = data.find(b'\r\n\r\n') + 4  # 找到HTTP头结束位置
        data = data[header_end:]  # 提取纯WebSocket数据帧部分
        
    if len(data) < 2:
        return None, data
    
    # 检查操作码
    opcode = data[0] & 0x0F
    if opcode != 0x01:  # 非文本帧
        return None, data[2:]
    
    masked = data[1] & 0x80
    payload_len = data[1] & 0x7F
    
    idx = 2
    if payload_len == 126:
        if len(data) < 4:
            return None, data
        payload_len = int.from_bytes(data[2:4], 'big')
        idx = 4
    elif payload_len == 127:
        return None, data  # 不支持超长消息
    
    if masked:
        if len(data) < idx + 4 + payload_len:
            return None, data
        mask = data[idx:idx+4]
        idx += 4
    else:
        if len(data) < idx + payload_len:
            return None, data
    
    payload = data[idx:idx+payload_len]
    
    if masked:
        payload = bytearray(payload)
        for i in range(len(payload)):
            payload[i] ^= mask[i % 4]
        payload = bytes(payload)
    
    try:
        return payload.decode('utf-8'), data[idx+payload_len:]
    except:
        return None, data[idx+payload_len:]

def ws_send(sock, message):
    """发送WebSocket消息"""
    try:
        msg_bytes = message.encode('utf-8')
        frame = bytearray([0x81])  # 文本帧
        
        if len(msg_bytes) < 126:
            frame.append(len(msg_bytes))
        else:
            frame.append(126)
            frame.extend(len(msg_bytes).to_bytes(2, 'big'))
        
        frame.extend(msg_bytes)
        sock.send(bytes(frame))
        return True
    except Exception as e:
        print(f"发送错误: {e}")
        return False
    

def start_websocket_server():
    """启动WebSocket服务器"""
    # 创建服务器socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", 80))
    server_socket.listen(3)  # 减少并发连接数
    print(f"🚀 WebSocket服务器已启动: ws://本机IP:8080")
    
    # 使用poll处理多客户端
    poll = select.poll()
    poll.register(server_socket, select.POLLIN)
    
    clients = {} 
    client_ids = {}
    next_client_id = 1
    
    try:
        while True:
            events = poll.poll(1000)  # 处理事件，设置超时避免忙等待，1秒超时
            for sock, event in events:
                if sock is server_socket:
                    client_sock, addr = server_socket.accept()
                    client_id = next_client_id
                    next_client_id += 1
                    clients[client_sock] = b''
                    client_ids[client_sock] = client_id
                    poll.register(client_sock, select.POLLIN)  
                    print(f"✅ 客户端 #{client_id} 连接: {addr}")
                    
                else:
                    # 处理客户端数据
                    try:
                        data = sock.recv(1024)
                        if data:
                            clients[sock] += data                     
                            # print("clients[sock]:",clients[sock][:200]) # 打印接收到的数据,为避免太长时打印，只打印前200个字符
                            if b'GET' in clients[sock] and b'Upgrade: websocket' in clients[sock]:
                                print("检测到WebSocket握手请求...")
                                if ws_handshake(sock, clients[sock]):
                                    # 检查是否是WebSocket握手请求
                                    client_id = client_ids[sock]
                                    print(f"🔗 客户端 #{client_id} WebSocket握手成功")
                                    ws_send(sock, ujson.dumps({"cmd_type":"websocket","connect_status":f"websocket连接成功! 你是客户端 #{client_id}"}))
                                    clients[sock] = b''  # 清空缓冲区
                            elif b'GET' in clients[sock] or b'POST' in clients[sock]:
                                print("检测到HTTP请求...")
                                # 处理除websocket建立链接之外的普通HTTP请求
                                try:
                                    request_json = parse_http_request(clients[sock])
                                    response = handle_http_request(request_json)
                                    sock.send(response.encode('utf-8')) # type: ignore
                                except Exception as e:
                                    print(f"处理HTTP请求出错: {e}")
                                    response = 'HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nInternal Server Error'
                                    sock.send(response.encode('utf-8'))
                                sock.close()
                                poll.unregister(sock)
                                del clients[sock]
                                del client_ids[sock]
                            else:
                                print("监测到WebSocket数据请求...")
                                # 处理WebSocket请求数据
                                while True:
                                    msg, remaining = ws_receive(clients[sock])
                                    if msg is None:
                                        break
                                    client_id = client_ids[sock]
                                    print(f"📥 客户端 #{client_id}: {msg[:100]}")                           
                                    response = handle_websocket_command(msg)
                                    ws_send(sock, response)
                                    print(f"📤 服务端: {response}")
                                    clients[sock] = remaining
                                    gc.collect()  # 及时回收内存
                        else:
                            # 客户端断开连接
                            client_id = client_ids.get(sock, '未知')
                            print(f"❌ 客户端 #{client_id} 断开连接")
                            poll.unregister(sock)
                            sock.close()
                            if sock in clients:
                                del clients[sock]
                            if sock in client_ids:
                                del client_ids[sock]
                                
                    except Exception as e:
                        # 客户端错误
                        client_id = client_ids.get(sock, '未知')
                        print(f"⚠️ 客户端 #{client_id} 错误: {e}")
                        poll.unregister(sock)
                        try:
                            sock.close()
                        except:
                            pass
                        if sock in clients:
                            del clients[sock]
                        if sock in client_ids:
                            del client_ids[sock]
            
            # 定期内存回收
            if ticks_ms() % 5000 < 100:  # 每5秒左右回收一次
                gc.collect()
                
    except KeyboardInterrupt:
        # 捕获用户主动中断退出
        print(f"🛑 服务器被用户停止！")
    except Exception as e:
        # 捕获其他错误
        print(f"💥 服务器错误: {e}！")
    finally:
        # 清理资源
        for sock in list(clients.keys()):
            try:
                poll.unregister(sock)
                sock.close()
            except:
                pass
        server_socket.close()
        print(f"🧹 服务器已关闭！")

# 启动服务器
if __name__ == "__main__":
    start_websocket_server()