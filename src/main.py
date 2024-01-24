import DB
import schedule
import KoreaInvest as ki
from datetime import datetime, timedelta

seq_no = ki.get_condition_search(ki.key, ki.secret)

def get_token():
    # 한투 접근을 위한 토큰 받아오기.
    # 그리고 조건검색의 seq_no 가져옴.

    current_utc_time = datetime.utcnow()
    current_time_utc9 = current_utc_time + timedelta(hours=9)
    formatted_time_utc9 = current_time_utc9.strftime("%Y-%m-%d %H:%M:%S")
    print(f"현재 시간 (UTC +9): {formatted_time_utc9}")

    print(f"새로운 토큰을 발급합니다.")
    ki.get_token()
    print(f"DB를 초기화하고 설정합니다.")
    DB.wipe_lists()
    print(f"설정완료!\n------------------------------------------\n")

def job():
    # 조건에 걸린 종목 가져오기.
    # 선택된 종목들의 등장 횟수를 판별해서 주문 까지 함.

    if ki.time_check() != 1:
        # 아직 장이 열리기 전임.
        print(f"오전 시장 시간이 아님!\n------------------------------------------\n")
        return

    own_stocks = ki.having_stock()
    if len(own_stocks) == DB.limit_cnt():
        print(f"현재 보유 주식이 최대치입니다.")
        print(f"다음 거래를 기다립니다.")
        return

    print(f"조건 검색 실시")

    stock_info = ki.get_stocks(seq_no)
    ki.select_stocks(stock_info)
    stocks = ki.now_looking()

    for item in stocks.keys():
        if item == "restart":
            continue
        print(f"종목코드: {item}, 탈출 횟수: {stocks[item]}")

    print(f"조건 검색 완료\n------------------------------------------\n")

schedule.every(30).seconds.do(job)
schedule.every(14).seconds.do(ki.sell_stock)
schedule.every().day.at("08:30:00").do(get_token)

while True:
    # 스케줄에 등록된 작업이 있는지 확인하고 실행
    schedule.run_pending()
