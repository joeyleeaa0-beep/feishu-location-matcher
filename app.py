import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
TABLE1_TOKEN = "PojNsqwFdhMZrHt6WEzcU45LncF"
TABLE2_TOKEN = "V6G7sm6xPhtpcGt0bgVcVEv3nYf"
RENDER_URL = os.environ.get("RENDER_URL", "")

TABLE2_SHEETS = [
    {"id": "1TTBGH", "city": "深圳"},
    {"id": "2sAdwn", "city": "上海"},
    {"id": "3DMFTo", "city": "成都"},
    {"id": "4iOHhP", "city": "天津"},
]

TABLE1_SHEETS = [
    {"id": "1SeQMO", "city_col": "A", "title_col": "D", "output_col": "T", "title_col_index": 3, "output_col_letter": "T"},
    {"id": "0VAckj", "city_col": "A", "title_col": "D", "output_col": "Q", "title_col_index": 3, "output_col_letter": "Q"},
    {"id": "2HSink", "city_col": "A", "title_col": "G", "output_col": "AE", "title_col_index": 6, "output_col_letter": "AE"},
    {"id": "3ByYkO", "city_col": "A", "title_col": "D", "output_col": "L", "title_col_index": 3, "output_col_letter": "L"},
]

def col_letter_to_index(col):
    result = 0
    for char in col.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1

def get_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    )
    return res.json()["tenant_access_token"]

def read_sheet(spreadsheet, sheet_range):
    access_token = get_token()
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + spreadsheet + "/values/" + sheet_range + "?valueRenderOption=ToString"
    res = requests.get(url, headers=headers)
    return res.json().get("data", {}).get("valueRange", {}).get("values", [])

def write_cell(spreadsheet, cell_range, value):
    access_token = get_token()
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + spreadsheet + "/values"
    requests.put(url, headers=headers, json={"valueRange": {"range": cell_range, "values": [[value]]}})

def match_location():
    try:
        # 建立表2匹配字典
        lookup = {}
        for sheet in TABLE2_SHEETS:
            sid = sheet["id"]
            city = sheet["city"]
            rows = read_sheet(TABLE2_TOKEN, sid + "!O2:R200")
            for row in rows:
                o_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                r_val = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                if o_val and r_val:
                    lookup[city + "|" + o_val[:10]] = r_val

        # 遍历表1所有sheet
        for t1sheet in TABLE1_SHEETS:
            sid = t1sheet["id"]
            title_idx = t1sheet["title_col_index"]
            out_col = t1sheet["output_col_letter"]
            out_idx = col_letter_to_index(out_col)
            end_col = out_col

            rows = read_sheet(TABLE1_TOKEN, sid + "!A2:AZ500")
            for i, row in enumerate(rows):
                row_num = i + 2
                a_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                d_val = str(row[title_idx]).strip() if len(row) > title_idx and row[title_idx] else ""
                t_val = str(row[out_idx]).strip() if len(row) > out_idx and row[out_idx] else ""

                if sid == "3ByYkO" and i < 5:
                    print("行" + str(row_num) + " A=" + a_val + " D=" + d_val[:10])
                        cell_range = sid + "!" + out_col + str(row_num) + ":" + out_col + str(row_num)
                        write_cell(TABLE1_TOKEN, cell_range, lookup[key])
                        print("写入 " + sid + " 第" + str(row_num) + "行")

        print("匹配完成")
    except Exception as e:
        print("错误: " + str(e))

def scheduler():
    while True:
        match_location()
        threading.Event().wait(30)

def keep_alive():
    while True:
        threading.Event().wait(840)
        if RENDER_URL:
            try:
                requests.get(RENDER_URL, timeout=5)
            except Exception:
                pass

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "OK"
    body = request.get_json(silent=True) or {}
    if "challenge" in body:
        return jsonify({"challenge": body["challenge"]})
    match_location()
    return jsonify({"ok": True})

t1 = threading.Thread(target=scheduler, daemon=True)
t1.start()

t2 = threading.Thread(target=keep_alive, daemon=True)
t2.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
