import json
import requests
import DB
import Gmail
from firebase_admin import db
from datetime import datetime, timedelta

key = db.reference("/APPKEY").get()
secret = db.reference("/SECRETKEY").get()
domain = "https://openapi.koreainvestment.com:9443"


def get_token():
    url = "/oauth2/tokenP"

    headers = {
        'content-type': 'application/json'
    }
    body = {
        "grant_type": "client_credentials",
        "appkey": key,
        "appsecret": secret
    }

    response = requests.request("POST", domain + url, headers=headers, data=json.dumps(body))
    data = response.json()
    db.reference().update({"access_token":data["access_token"]})

def get_condition_search(key, secret):
    url = "/uapi/domestic-stock/v1/quotations/psearch-title"

    headers = {
        'content-type': 'application/json',
        'authorization': "Bearer " + db.reference("/access_token").get(),
        "appkey": key,
        "appsecret": secret,
        "tr_id": "HHKST03900300",
        "custtype": "P"
    }

    body = {
        "user_id": db.reference("/HTS_ID").get()
    }

    response = requests.request("GET", domain + url, headers=headers, params=body)
    data = response.json()
    lists = data["output2"]
    target_condition = lists[0]["seq"]
    return target_condition

def get_stocks(seq_no):
    url = "/uapi/domestic-stock/v1/quotations/psearch-result"

    headers = {
        'content-type': 'application/json',
        'authorization': "Bearer " + db.reference("/access_token").get(),
        "appkey": key,
        "appsecret": secret,
        "tr_id": "HHKST03900400",
        "custtype": "P"
    }

    body = {
        "user_id": db.reference("/HTS_ID").get(),
        "seq": seq_no
    }

    response = requests.request("GET", domain + url, headers=headers, params=body)
    data = response.json()

    if "output2" not in data:
        return {}
        
    temp = data["output2"]
    lists = {}
    for item in temp:
        if int(float(item["acml_vol"].strip())) <= 1000000:
            continue
        lists[item["code"]] = int(float(item["price"]))
    return lists

def now_looking():
    candidate = db.reference("/candidate").get()
    return candidate

def select_stocks(stock_info):
    from_DB = db.reference("/20second").get()
    candidate = db.reference("/candidate").get()

    # 모든 종목 코드들을 가져오기 stock_info, from DB
    # stock (O), fromDB (X) => 등장
    # stock (X), fromDB (O) => 탈출
    # stock (0), fromDB (O) => 유지
    # candidate == 2, 등장 했으면 포착 완료
    keys_combined = list(from_DB.keys() | stock_info.keys())
    for item in keys_combined:
        # 주식이 사라지는 경우를 확인.
        if item == "restart":
            continue

        if item in candidate:
            if candidate[item] == 1 and (item in stock_info and item not in from_DB):
                candidate[item] += 1
                print(f"한투: 종목 {item} 포착완료")

                cnt = db.reference("/cnt").get()
                if cnt < 3:
                    print(f"보유한 종목이 {cnt}개로 주문 가능, 주문 시작!")
                    Gmail.send_email(f"한투: 종목코드 {item}이 조건을 만족하였습니다.")
                    balance = db.reference("/balance").get()
                    #order_stock(item, int(balance / stock_info[item]), "BUY")

                    db.reference().update({f"cnt": cnt + 1})
                    print(f"주문완료!\n")

        if item not in stock_info and item in from_DB:
            if item not in candidate:
                candidate[item] = 0
            candidate[item] += 1

    stock_info["restart"] = 0
    db.reference().update({f"/20second": None})
    for item in stock_info.keys():
        db.reference().update({f"/20second/{item}": stock_info[item]})
    for item in candidate.keys():
        db.reference().update({f"/candidate/{item}": candidate[item]})
    return 0

def having_stock():
    account = db.reference("/account").get()
    first, second = account.split("-")
    token = db.reference("/access_token").get()
    Client_ID = db.reference("/APPKEY").get()
    Client_Secret = db.reference("/SECRETKEY").get()

    url = "/uapi/domestic-stock/v1/trading/inquire-balance"

    body = {
        "CANO": f"{first}",
        "ACNT_PRDT_CD": f"{second}",
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "N",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    headers = {
        "authorization": f"Bearer {token}",
        "appKey": f"{Client_ID}",
        "appSecret": f"{Client_Secret}",
        "tr_id": "TTTC8434R"
    }

    res = requests.get(domain + url, params=body, headers=headers)
    data = json.loads(res.text)
    stocks = []

    for item in data["output1"]:
        qty = int(item["hldg_qty"])
        if qty == 0:
            continue

        no = item["pdno"]
        name = item["prdt_name"]
        buy_price = int(float(item["pchs_avg_pric"]))
        now_price = int(float(item["prpr"]))
        stocks.append((no, name, qty, buy_price, now_price))

    return stocks

def time_check():
    # 현재 시간을 얻어옵니다.
    now_utc = datetime.utcnow()
    now_kst = now_utc + timedelta(hours=9)  # UTC+9 기준으로 변환합니다.

    formatted_time_utc9 = now_kst.strftime("%Y-%m-%d %H:%M:%S")
    print(f"현재 시간 (UTC +9): {formatted_time_utc9}")

    is_after_9am = now_kst.time() >= datetime.strptime('09:00:00', '%H:%M:%S').time()
    is_before_2pm = now_kst.time() < datetime.strptime('15:30:00', '%H:%M:%S').time()
    return is_after_9am and is_before_2pm

def sell_stock():
    if time_check() != 1:
        # 아직 장이 열리기 전임.
        print(f"오전 시장 시간이 아님!\n------------------------------------------\n")
        return

    own_stocks = having_stock()
    print(f"현재 보유하고 있는 주식의 수 : {len(own_stocks)}개, 수익률 확인\n")

    for item in own_stocks:
        no, name, qty, buy_price, now_price = item
        loss = (now_price - buy_price) / buy_price * 100

        print(f"현재 보유하고 있는 주식: {name}, 변동률 {round(loss, 3)}%")
        # # loss <= -4 or
        # if 8 <= loss:
        #     order_stock(no, qty, "SELL")
        #     print(f"한투: 종목 {name}의 수익률이 {round(loss, 3)}%로 매도 하였습니다.")
        #     Gmail.send_email(f"한투: 종목 {name}의 수익률이 {round(loss, 3)}%로 매도 하였습니다.")
        #     cnt = db.reference("/cnt").get()
        #     db.reference().update({f"cnt": cnt - 1})
    print(f"sell_Stock 종료\n")

    return

def order_stock(code, qty, position):
    account = db.reference("/account").get()
    first, second = account.split("-")
    token = db.reference("/access_token").get()
    Client_ID = db.reference("/APPKEY").get()
    Client_Secret = db.reference("/SECRETKEY").get()

    url = "/uapi/domestic-stock/v1/trading/order-cash"

    body = {
        "CANO": f"{first}",
        "ACNT_PRDT_CD": f"{second}",
        "PDNO": f"{code}",
        "ORD_DVSN": "01",
        "ORD_QTY": f"{qty}",
        "ORD_UNPR": "0"
    }
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appKey": f"{Client_ID}",
        "appSecret": f"{Client_Secret}",
        "tr_id": "TTTC0802U" if position == "BUY" else "TTTC0801U"
    }

    res = requests.post(domain + url, data=json.dumps(body), headers=headers)
    rescode = res.status_code

    print(f"한투: 종목코드 {code} 매수 완료")
    Gmail.send_email(f"한투: 종목코드 {code} 매수 완료")
    return


if __name__ == '__main__':
    sell_stock()
    # get_token()
    # seq_no = get_condition_search(key, secret)
    #
    # stock_info = get_stocks(seq_no)
    # select_stocks(stock_info)
    # order_stock("189690", 1)
