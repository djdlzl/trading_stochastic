import json
import requests
from requests.exceptions import RequestException
from utils.string_utils import unicode_to_korean
from datetime import datetime, timedelta


class KISMarketData:
    def __init__(self, auth):
        self.auth = auth  # KISAuth 인스턴스
######################################################################################
#########################    상한가 관련 메서드   #######################################
######################################################################################

    def get_stock_price(self, ticker):
        """
        지정된 종목의 현재 주가 정보를 가져옵니다.

        Args:
            ticker (str): 종목 코드

        Returns:
            dict: 주가 정보를 포함한 딕셔너리
        """
        self.auth._set_headers(is_mock=False, tr_id="FHPST01010000")
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price-2"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker
        }
        response = requests.get(url=url, params=params, headers=self.headers, timeout=10)
        json_response = response.json()
        # print(json.dumps(json_response,indent=2))

        return json_response


    def get_upper_limit_stocks(self):
        """
        상한가 종목 목록을 가져옵니다.

        Returns:
            dict: 상한가 종목 정보를 포함한 딕셔너리
        """
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/capture-uplowprice"
        body = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "11300",
            "FID_PRC_CLS_CODE": "0",
            "FID_DIV_CLS_CODE": "0",
            "FID_INPUT_ISCD": "0000",
            "FID_TRGT_CLS_CODE": "",
            "FID_TRGT_EXLS_CLS_CODE": "",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": ""
        }
        self._get_hashkey(body, is_mock=False)
        self.auth._set_headers(is_mock=False, tr_id="FHKST130000C0")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.get(url=url, headers=self.headers, params=body, timeout=10)
        
        upper_limit_stocks = response.json()
        return upper_limit_stocks


    def get_upAndDown_rank(self):
        """
        상승/하락 순위 정보를 가져옵니다.

        Returns:
            dict: 상승/하락 순위 정보를 포함한 딕셔너리
        """
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/ranking/fluctuation"
        body = {
            "fid_cond_mrkt_div_code":"J",
            "fid_cond_scr_div_code":"20170",
            "fid_input_iscd":"0000",
            "fid_rank_sort_cls_code":"0",
            "fid_input_cnt_1":"0",
            "fid_prc_cls_code":"0",
            "fid_input_price_1":"",
            "fid_input_price_2":"",
            "fid_vol_cnt":"",
            "fid_trgt_cls_code":"0",
            "fid_trgt_exls_cls_code":"0",
            "fid_div_cls_code":"0",
            "fid_rsfl_rate1":"18",
            "fid_rsfl_rate2":"29.5",
            "fid_input_date_1": "20240314",
            "fid_input_date_2": "20241124"
        }
        
        self._get_hashkey(body, is_mock=False)
        self.auth._set_headers(is_mock=False, tr_id="FHPST01700000")
        self.headers["hashkey"] = self.hashkey
        
        response = requests.get(url=url, headers=self.headers, params=body, timeout=10)
        
        updown = response.json()
        # print('상승 종목: ',json.dumps(updown, indent=2, ensure_ascii=False))
        return updown


    def print_korean_response(self, response):
        """
        API 응답의 한글 내용을 정리된 JSON 형식으로 출력합니다.

        Args:
            response (dict): API 응답 딕셔너리
        """
        def unicode_to_korean_converter(obj):
            return unicode_to_korean(obj) if isinstance(obj, str) else obj

        formatted_response = json.loads(json.dumps(response, default=unicode_to_korean_converter))
        print(json.dumps(formatted_response, ensure_ascii=False, indent=2))

    def get_current_price(self, ticker):
        """
        지정된 종목의 현재 주가 정보를 가져옵니다.

        Args:
            ticker (str): 종목 코드

        Returns:
            float: 현재 주가
        """
        stock_price_info = self.get_stock_price(ticker)

        return stock_price_info.get('output').get('stck_prpr'), stock_price_info.get('output').get('trht_yn') # 현재가 반환, 기본값은 0


######################################################################################
################################    종목 조회   ###################################
######################################################################################

    def get_volume_rank(self):
        """ 거래량 상위 종목 조회 """
        self.auth._set_headers(tr_id="FHPST01710000")
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/volume-rank"
        body = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }

        response = requests.get(url=url, params=body, headers=self.headers, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        # print(json.dumps(response_json, indent=2, ensure_ascii=False))
        
        return response_json

    
    
    def get_stock_volume(self, ticker, days=3):
        """
        지정된 종목의 최근 n일간의 거래량을 가져옵니다.
        
        Args:
            ticker (str): 종목 코드
            days (int): 조회할 일 수 (기본값: 3)
        
        Returns:
            list: 최근 n일간의 거래량 리스트 (최신 날짜부터 과거 순으로)
        """
        
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
        
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        body = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
            # "ST_DATE": start_date,
            # "END_DATE": end_date
        }
        self._get_hashkey(body, is_mock=False)
        self.auth._set_headers(is_mock=False, tr_id="FHKST01010400")
        
        response = requests.get(url=url, params=body, headers=self.headers, timeout=10)
        json_response = response.json()
        
        # print(json.dumps(json_response, indent=2, e_ascii=False))
        
        volumes = []
        for item in json_response.get('output', []):
            volumes.append(int(item.get('acml_vol', '0')))
        
        return volumes[:days]  # 최근 n일간의 거래량만 반환
    
    def compare_volumes(self, volumes):
        """
        3일간의 거래량을 비교하고 차이를 백분율로 계산합니다.
        
        Args:
            volumes (list): 3일간의 거래량 리스트 (최신 날짜부터 과거 순으로)
        
        Returns:
            tuple: (1일 전과 2일 전의 차이 백분율, 2일 전과 3일 전의 차이 백분율)
        """
        if len(volumes) != 3:
            raise ValueError("3일간의 거래량 데이터가 필요합니다.")
        
        day1, day2, day3 = volumes
        
        diff_1_2 = ((day1 - day2) / day2) * 100 if day2 != 0 else float('inf')
        diff_2_3 = ((day2 - day3) / day3) * 100 if day3 != 0 else float('inf')
        
        return round(diff_1_2, 2), round(diff_2_3, 2)
    
    def get_basic_stock_info(self, ticker):
        self.auth._set_headers(tr_id="FHPST01710000")
        url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/search-stock-info"
        body = {
            "PRDT_TYPE_CD": "300",
            "PDNO": ticker
        }

        self._get_hashkey(body, is_mock=False)
        self.auth._set_headers(is_mock=False, tr_id="CTPF1002R")
        self.headers["hashkey"] = self.hashkey

        response = requests.get(url=url, params=body, headers=self.headers, timeout=10)
        response.raise_for_status()
        response_json = response.json()
        # print(json.dumps(response_json, indent=2, ensure_ascii=False))
        
        return response_json
