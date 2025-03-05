import json
import requests
import datetime
from config.config import M_ACCOUNT_NUMBER

class KISOrder:
    def __init__(self, auth):
        self.auth = auth  # KISAuth 인스턴스

    def place_order(self, ticker, quantity, order_type=None, price=None):
        """
        주식 주문을 실행합니다.

        Args:
            ticker (str): 종목 코드
            order_type (str): 주문 유형
            quantity (int): 주문 수량

            Returns:
            dict: 주문 실행 결과를 포함한 딕셔너리
        """
        
        if order_type == 'buy':
            tr_id_code = "VTTC0802U"
        elif order_type == 'sell':
            tr_id_code = "VTTC0801U"
        else:
            raise ValueError("Invalid order type. Must be 'buy' or 'sell'.")  # 추가된 코드: 잘못된 주문 유형 처리
        
        self.auth._set_headers(is_mock=True, tr_id=tr_id_code)
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        data = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "PDNO": ticker,
            "ORD_DVSN": "01" if price is None else "00",  # 01: 시장가, 00: 지정가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0" if price is None else str(price),
        }
        self.headers["hashkey"] = None

        response = requests.post(url=url, data=json.dumps(data), headers=self.headers, timeout=10)
        json_response = response.json()

        return json_response


    def sell_order(self, ticker, quantity, price=None):
        """
        주식 매도 주문을 실행합니다.

        Args:
            ticker (str): 종목 코드
            quantity (int): 매도 수량
            price (float, optional): 매도 희망 가격. None이면 시장가 주문

        Returns:
            dict: 주문 실행 결과를 포함한 딕셔너리
        """
        self.auth._set_headers(is_mock=True, tr_id="VTTC0801U")  # 매도 거래 ID
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-cash"
        
        data = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "PDNO": ticker,
            "ORD_DVSN": "01" if price is None else "00",  # 01: 시장가, 00: 지정가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": "0" if price is None else str(price),
        }
        self.headers["hashkey"] = None

        response = requests.post(url=url, data=json.dumps(data), headers=self.headers, timeout=10)
        json_response = response.json()

        return json_response


    def cancel_order(self, order_num):
        """
        주문취소 API
        """
        
        # 주문번호는 8자리로 맞춰야 함
        order_num = str(order_num).zfill(8)
        
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-rvsecncl"
        body = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "KRX_FWDG_ORD_ORGNO": "",
            "ORGN_ODNO": order_num,
            "ORD_DVSN": "01",
            "RVSE_CNCL_DVSN_CD": "02", # 취소주문
            "ORD_QTY": "0",
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y"
        }

        self._get_hashkey(body, is_mock=True)
        self.auth._set_headers(is_mock=True, tr_id="VTTC0803U")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.post(url=url, headers=self.headers, json=body, timeout=10)
        json_response = response.json()
        
        return json_response


    def revise_order(self, order_num):
        """
        주문취소 API
        """
        print("revise_order:- ",order_num, type(order_num))
        
        # 주문번호는 8자리로 맞춰야 함
        order_num = str(order_num).zfill(8)
        
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/order-rvsecncl"
        body = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "KRX_FWDG_ORD_ORGNO": "00950",
            "ORGN_ODNO": order_num,
            "ORD_DVSN": "01",
            "RVSE_CNCL_DVSN_CD": "01", # 01:정정, 02:취소
            "ORD_QTY": "0",
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y",
            "ALGO_NO": ""
        }
        self._get_hashkey(body, is_mock=True)
        self.auth._set_headers(is_mock=True, tr_id="VTTC0803U")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.post(url=url, headers=self.headers, json=body, timeout=10)
        json_response = response.json()
        
        return json_response


    def purchase_availability_inquiry(self, ticker=None):
        """
        주문가능조회
        """
        url = "https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-psbl-order"
        body = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "PDNO": "" if ticker is None else ticker,
            "ORD_UNPR": "",
            "ORD_DVSN": "01",
            "CMA_EVLU_AMT_ICLD_YN": "N",
            "OVRS_ICLD_YN": "N"
        }
        
        self._get_hashkey(body, is_mock=True)
        self.auth._set_headers(is_mock=True, tr_id="VTTC8908R")
        self.headers["hashkey"] = self.hashkey

        response = requests.get(url=url, headers=self.headers, params=body, timeout=10)
        json_response = response.json()
        
        return json_response
    
######################################################################################
################################    잔고 메서드   ###################################
######################################################################################

    def daily_order_execution_inquiry(self, order_num):
        """
        주식일별주문체결조회
        """
        today = datetime.now()
        formatted_date = today.strftime('%Y%m%d')
        # url="https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        url="https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        body = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "INQR_STRT_DT": formatted_date,
            "INQR_END_DT": formatted_date,
            "UNPR_DVSN": "01",
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": "", # 상품번호 ticker, 공란 - 전체조회
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": order_num,
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        self._get_hashkey(body, is_mock=True)
        self.auth._set_headers(is_mock=True, tr_id="VTTC8001R")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.get(url=url, headers=self.headers, params=body, timeout=10)
        json_response = response.json()
        print("daily_order_execution_inquiry 정상 실행")
        
        
        return json_response





    def balance_inquiry(self):

        # url="https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        url="https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance"
        body = {
            "CANO": M_ACCOUNT_NUMBER,
            "ACNT_PRDT_CD": "01",
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N", 
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
                
        self._get_hashkey(body, is_mock=True)
        self.auth._set_headers(is_mock=True, tr_id="VTTC8434R")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.get(url=url, headers=self.headers, params=body, timeout=10)
        json_response = response.json()
        
        return json_response.get("output1")
    