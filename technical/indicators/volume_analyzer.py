import pandas as pd
from typing import Dict


class VolumeAnalyzer:
    def calculate_volume_indicators(self, prices: pd.Series, volumes: pd.Series) -> Dict:
        if prices.empty or volumes.empty:
            return {}
        
        avg_volume = volumes.shift(1).rolling(20).mean()
        current_volume = volumes.iloc[-1] if not volumes.empty else None
        avg_vol = float(avg_volume.iloc[-1]) if not avg_volume.empty else None
        
        volume_ratio = None
        if current_volume is not None and avg_vol is not None and avg_vol > 0:
            volume_ratio = current_volume / avg_vol
        
        return {
            'current_volume': float(current_volume) if current_volume is not None else None,
            'avg_volume_20': avg_vol if not pd.isna(avg_vol) else None,
            'volume_ratio': float(volume_ratio) if volume_ratio is not None else None,
        }

