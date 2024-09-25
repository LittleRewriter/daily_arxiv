import datetime
import time
import requests
import json
from datetime import timedelta
from functools import reduce
import xml.etree.ElementTree as ET
import os

from tencentcloud.common import credential
from tencentcloud.tmt.v20180321.tmt_client import TmtClient
from tencentcloud.tmt.v20180321.models import TextTranslateRequest

isEmpty = True

arxiv_cat_mapping = {
    "cs.AI" : "人工智能",
    "cs.AR": "硬件结构",
    "cs.CL": "计算语言",
    "cs.CV": "视觉",
    "cs.CG": "计算几何",
    "cs.CR": "密码学",
    "cs.DB": "数据库",
    "cs.DC": "并行计算",
    "cs.FL": "形式语义",
    "cs.GR": "图形学",
    "cs.HC": "人机交互",
    "cs.PF": "高性能",
    "cs.LG": "机器学习",
    "cs.MM": "多媒体",
    "cs.NA": "数值分析",
    "cs.NI": "网络体系结构",
    "cs.PL": "编程语言",
    "cs.SI": "社交网络",
    "eess.SY": "控制系统",
    "physics.comp-ph": "计算物理",
    "physics.flu-dyn": "计算流体"
}

def replace_arxiv_cat(cat: str) -> str:
    if cat in arxiv_cat_mapping:
        return arxiv_cat_mapping[cat]
    else:
        return cat

class arxiv_entry:
    def __init__(self, id: str, pub: str, upd: str, cat: str, title: str, abs: str, imp: bool) -> None:
        self.id: str = id
        self.pub: str = pub
        self.upd: str = upd
        self.cat: str = cat
        self.title: str = title
        self.abs: str = abs
        self.important: bool = imp
        
    def sim_id(self) -> str:
        return self.id.split('/')[4].split('v')[0]
    
    def __repr__(self) -> str:
        return f"<{self.sim_id()}|{self.pub}>:{self.title}"
    

def get_arxiv_result(ent_py: dict,  query_cat: str, max_result: int, date: str, imp: bool):
    get_url = f"https://export.arxiv.org/api/query?search_query=cat:{query_cat}&start=0&max_results={max_result}&sortBy=lastUpdatedDate&sortOrder=descending"
    xml = requests.get(get_url).text
    xml = reduce(lambda x, y: x + "\n" + y, xml.replace(" xmlns=\"http://www.w3.org/2005/Atom\"", "").split("\n")[1:]) 
    tree = ET.fromstring(xml)
    entries = tree.findall("entry")
    for ent in entries:
        id = ent.find("id").text
        pub = ent.find("published").text
        title = ent.find("title").text
        upd = ent.find("updated").text
        summ = ent.find("summary").text.replace('\n', ' ')
        cat = ';'.join([replace_arxiv_cat(e.attrib["term"]) for e in ent.findall("category")])
        if pub.find(date) != -1 or (imp and upd.find(date) != -1):
            n_entry = arxiv_entry(id, pub, upd, cat, title, summ, imp)
            ent_py[n_entry.sim_id()] = n_entry
    time.sleep(3)

def get_translate(client: TmtClient, cont: str) -> str:
    req = TextTranslateRequest()
    req.SourceText = cont
    req.Source = "en"
    req.Target = "zh"
    req.ProjectId = 0
    return client.TextTranslate(req).TargetText
    
def get_code(client: TmtClient, ent_py: dict[str, arxiv_entry]):
    base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
    cnt = 0

    content: dict[str, str] = dict()
    cnt = 0
    for k,v in ent_py.items():
        url = base_url + k
        if cnt % 10 == 0:
            print(f"get code {cnt+1} / {len(ent_py)}")
        cnt = cnt + 1
        try:
            r = requests.get(url).json()
            if "official" in r and r["official"]:
                repo_url = r["official"]["url"]
                repo_name = repo_url.split("/")[-1]
                trans_abs = get_translate(client, v.abs)
                content[k] = f"[{v.title}]({v.id})\n\n领域：{v.cat}\n\n代码：[{repo_name}]({repo_url})\n\n摘要：{trans_abs}\n\n"
                time.sleep(0.25)
            elif v.important:
                trans_abs = get_translate(client, v.abs)
                content[k] = f"[{v.title}]({v.id})\n\n领域：{v.cat}\n\n摘要：{trans_abs}\n\n"
                time.sleep(0.25)
        except Exception as e:
            print(f"exception: {e} with id: {k}")
    return content

import hmac
import hashlib
import base64
import urllib.parse

def send_ding(title: str, msg: str, secret: str, access_token: str):
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    ding_id = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    
    res = requests.post(ding_id, headers={'Content-Type': 'application/json'}, json={'msgtype': 'markdown', 'markdown': { 'title': title, 'text': msg }})
    print(res.text)

if __name__ == "__main__":
    id = os.environ.get("TX_ID")
    key = os.environ.get("TX_KEY")
    ding_tok = os.environ.get("DING_URL")
    ding_sec = os.environ.get("DING_SEC")
    timestamp = str(round(time.time() * 1000))
    cred = credential.Credential(id, key)
    client = TmtClient(cred, "ap-beijing")
    DateToday = datetime.date.today()
    # N = 2 # 往前查询的天数
    # data_all = []
    day = str(DateToday + timedelta(-1))
    print(day)
    #     # you can add the categories in cats
    imp_cats = ["cs.gr", "cs.dc"]
    cats = [
        "cs.cv", "cs.hc", "cs.ai", "physics.comp-ph", "physics.flu-dyn", "cs.na"
    ]
    res = dict()
    for s in imp_cats:
        get_arxiv_result(res, s, 100, day, True)
        print(f"import cat {s}, sum result {len(res)}")
    for s in cats:
        get_arxiv_result(res, s, 100, day, False)
        print(f"cat {s}, sum result {len(res)}")
    fmt_md = get_code(client, res)
    
    if len(fmt_md) == 0:
        send_ding(str(DateToday), "今天是休假喵~", ding_sec, ding_tok)
    else:
        res_str = ""
        idx = 1
        for k, v in fmt_md.items():
            if len(res_str.encode()) + len(v.encode()) > 19000:
                send_ding(f"{DateToday}-{idx}", res_str, ding_sec, ding_tok)
                res_str = ""
                idx += 1
                time.sleep(1)
            res_str += v
        send_ding(f"{DateToday}-{idx}", res_str, ding_sec, ding_tok)
    
