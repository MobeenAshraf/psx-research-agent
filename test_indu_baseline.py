import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "packages" / "web"))
sys.path.insert(0, str(Path(__file__).parent / "packages" / "analysis"))

from psx_web.handlers import technical_analysis_handler, financial_analysis_handler


def test_technical_analysis(symbol: str):
    print(f"\n=== Technical Analysis for {symbol} ===")
    result = technical_analysis_handler.get_technical_analysis(symbol)
    
    if result.get('status') == 'error':
        print(f"ERROR: {result.get('error')}")
        return None
    
    output = {
        'symbol': result.get('symbol'),
        'recommendation': result.get('recommendation'),
        'confidence': result.get('confidence'),
        'indicators_count': len(result.get('indicators', {})),
        'reasoning_count': len(result.get('reasoning', []))
    }
    print(json.dumps(output, indent=2))
    return result


def test_financial_analysis(symbol: str):
    print(f"\n=== Financial Analysis for {symbol} ===")
    
    check_result = financial_analysis_handler.check_latest_report(symbol)
    print(f"Check result: {check_result.get('status')}")
    
    if check_result.get('status') == 'exists':
        print("Analysis already exists, skipping run")
        return check_result
    
    run_result = financial_analysis_handler.run_financial_analysis(symbol)
    print(f"Run result: {run_result.get('status')}")
    
    import time
    print("Waiting 30 seconds for analysis to start...")
    time.sleep(30)
    
    return run_result


if __name__ == "__main__":
    symbol = "INDU"
    
    print("=" * 60)
    print("BASELINE TEST FOR INDU")
    print("=" * 60)
    
    tech_result = test_technical_analysis(symbol)
    fin_result = test_financial_analysis(symbol)
    
    baseline = {
        'symbol': symbol,
        'technical_analysis': tech_result,
        'financial_analysis': fin_result
    }
    
    output_file = Path("baseline_indu_output.json")
    with open(output_file, 'w') as f:
        json.dump(baseline, f, indent=2, default=str)
    
    print(f"\nBaseline saved to {output_file}")

