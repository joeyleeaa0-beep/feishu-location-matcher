import os
import requests
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET")
TABLE1_TOKEN = "PojNsqwFdhMZrHt6WEzcU45LncF"
TABLE1_SHEET = "1SeQMO"
TABLE2_TOKEN = "V6G7sm6xPhtpcGt0bgVcVEv3nYf"
RENDER_URL = os.environ.get("RENDER_URL", "")

SHEETS = [
    {"id": "1TTBGH", "city": "深圳"},
    {"id": "2sAdwn", "city": "上海"},
    {"id": "3DMFTo", "city": "成都"},
    {"id": "4iOHhP", "city": "天津"},
]

def get_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    )
    return res.json()["tenant_access_token"]

def read_sheet(token, spreadsheet, sheet_range):
    access_token = get_token()
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + spreadsheet + "/values/" + sheet_range
    res = requests.get(url, headers=headers)
    return res.json().get("data", {}).get("valueRange", {}).get("values", [])

def write_cell(token, spreadsheet, cell_range, value):
    access_token = get_token()
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + spreadsheet + "/values"
    requests.put(url, headers=headers, json={"valueRange": {"range": cell_range, "values": [[value]]}})

def match_location():
    try:
        lookup = {}
        for sheet in SHEETS:
            sid = sheet["id"]
            city = sheet["city"]
            rows = read_sheet(TABLE2_TOKEN, TABLE2_TOKEN, sid + "!O2:R200")
            for row in rows:
                o_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                r_val = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                if o_val and r_val:
                    lookup[city + "|" + o_val[:10]] = r_val

        rows = read_sheet(TABLE1_TOKEN, TABLE1_TOKEN, TABLE1_SHEET + "!A2:T500")
        for i, row in enumerate(rows):
            row_num = i + 2
            a_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            d_val = str(row[3]).strip() if len(row) > 3 and row[3] else ""
            t_val = str(row[19]).strip() if len(row) > 19 and row[19] else ""

            if a_val and d_val and not t_val:
                key = a_val + "|" + d_val[:10]
                if key in lookup:
                    cell_range = TABLE1_SHEET + "!T" + str(row_num) + ":T" + str(row_num)
                    write_cell(TABLE1_TOKEN, TABLE1_TOKEN, cell_range, lookup[key])
                    print("写入第" + str(row_num) + "行")

        print("完成")
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
