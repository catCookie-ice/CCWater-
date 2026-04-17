import re
import os
import json
import http.client

# --- 数据解析与格式校验 ---
def parse_data(file_path):
    data = {}
    title = None
    if not os.path.exists(file_path):
        return data, title

    pattern = re.compile(r'(?: -)?([^：\s\-]+)：?([\d.]+)(?:mm)?')
    last_main_city = None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            is_first_non_empty = True
            for line in f:
                raw_line = line.strip()
                if not raw_line: continue
                
                if is_first_non_empty:
                    is_first_non_empty = False
                    if raw_line.startswith("#"):
                        title = raw_line[1:].strip()
                        continue
                
                if raw_line.startswith("-") and last_main_city:
                    matches = pattern.findall(raw_line)
                    for sub_city, value in matches:
                        sub_name = sub_city.strip()
                        val_float = float(value)
                        data[last_main_city][sub_name] = data[last_main_city].get(sub_name, 0.0) + val_float
                    continue

                if "：" in raw_line:
                    parts = raw_line.split("：", 1)
                    main_city = parts[0].strip()
                    rest = parts[1].strip()
                    
                    last_main_city = main_city
                    if last_main_city not in data:
                        data[last_main_city] = {}
                    
                    if rest:
                        matches = pattern.findall(rest)
                        for sub_city, value in matches:
                            sub_name = sub_city.strip()
                            val_float = float(value)
                            data[last_main_city][sub_name] = data[last_main_city].get(sub_name, 0.0) + val_float
    except Exception as e:
        print(f"解析文件 {file_path} 出错: {e}")

    return data, title

def save_data_to_file(file_path, data, title=None):
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if title:
                f.write(f"# {title}\n")
            for main_city in sorted(data.keys()):
                subs = data[main_city]
                f.write(f"{main_city}：\n")
                for sub, val in sorted(subs.items()):
                    f.write(f" -{sub}：{val:.1f}mm\n")
        return True
    except Exception as e:
        print(f"保存文件 {file_path} 出错: {e}")
        return False

def validate_file_format(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "：" not in content: return False
        return True
    except:
        return False

# --- DeepSeek API 调用 ---
def query_deepseek(region_name, api_key, api_host):
    if not api_key:
        return None
    prompt = f"""
    请查找“{region_name}”及其下属地区的年平均降水量数据。
    要求：
    1. 如果输入是省（如“陕西”），请列出该省下属主要地级市的数据，且每个地级市必须包含其下属区/县的详细降水量。
    2. 如果输入是地级市（如“咸阳市”），请列出其下属所有的区、县、县级市的数据。
    3. 如果输入是区/县级（如“秦都区”），则只返回该地区及其所属地级市的数据。
    4. 必须返回规范的行政区划全称（如“咸阳市”、“秦都区”）。
    5. 年降水量必须以毫米（mm）为单位。
    6. 严格按照以下 JSON 格式返回，不要有任何其他文字：
    {{
        "title": "XX地区降水量统计",
        "cities": [
            {{
                "main_city": "XX市",
                "results": [
                    {{"sub_city": "XX区/县", "rainfall": 数值}},
                    ...
                ]
            }},
            ...
        ]
    }}
    """
    
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的地理和气象数据助手。"},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "stream": False
    })
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        conn = http.client.HTTPSConnection(api_host)
        conn.request("POST", "/v1/chat/completions", payload, headers)
        res = conn.getresponse()
        data = res.read()
        json_res = json.loads(data.decode("utf-8"))
        content = json_res['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        print(f"DeepSeek 调用失败: {e}")
        return None
