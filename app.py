import os
import requests
import datetime
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

def get_feishu_token():
    res = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    )
    return res.json()["tenant_access_token"]

def match_shared_location():
    try:
        access_token = get_feishu_token()
        headers = {"Authorization": "Bearer " + access_token}

        # 读取表2所有城市数据，建立匹配字典
        lookup = {}
        for sheet in SHEETS:
            sheet_id = sheet["id"]
            city = sheet["city"]
            range_str = sheet_id + "!O2:R200"
            res = requests.get(
                "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + TABLE2_TOKEN + "/values/" + range_str,
                headers=headers
            )
            rows = res.json().get("data", {}).get("valueRange", {}).get("values", [])
            for row in rows:
                o_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
                r_val = str(row[3]).strip() if len(row) > 3 and row[3] else ""
                if o_val and r_val:
                    key = city + "|" + o_val[:10]
                    lookup[key] = r_val

        # 读取表1 A列、D列、T列
        range_str = TABLE1_SHEET + "!A2:T500"
        res = requests.get(
            "https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/" + TABLE1_TOKEN + "/values/" + range_str,
            headers=headers
        )
        rows = res.json().get("data", {}).get("valueRange", {}).get("values", [])

        for i, row in enumerate(rows):
            row_num = i + 2
            a_val = str(row[0]).strip() if len(row) > 0 and row[0] else ""
            d_val = str(row[3]).strip() if len(row) > 3 and row[3] else ""
            t_val = str(row[19]).strip() if len(row) > 19 and row[19] else ""

            if a_val and d_val and not t_val:
                key = a_val + "|" + d_val[:10]
                if key in lookup:
                    location = lookup[key]
