import json
import sys
from process.test_process import TestProcess

def extract_hts_kor_isnm():
    # Create an instance of TestProcess
    test_process = TestProcess()
    
    # Get the stock rank data
    stock_rank = test_process.kis_api.get_volume_rank()
    
    # Extract only the hts_kor_isnm values
    hts_kor_isnm_values = []
    
    # Check if output1 exists in the response
    if 'output1' in stock_rank and isinstance(stock_rank['output1'], list):
        for item in stock_rank['output1']:
            if 'hts_kor_isnm' in item:
                hts_kor_isnm_values.append(item['hts_kor_isnm'])
    
    # Print the extracted values
    print("\n=== hts_kor_isnm values ===\n")
    for i, value in enumerate(hts_kor_isnm_values, 1):
        print(f"{i}. {value}")
    
    return hts_kor_isnm_values

if __name__ == "__main__":
    extract_hts_kor_isnm()
