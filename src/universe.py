def master_universe(extra=None):
    US_CORE = [
        "SPY","QQQ","DIA","IWM",
        "AAPL","MSFT","GOOGL","AMZN","META","NFLX",
        "NVDA","AMD","AVGO","TSM","ASML","INTC","QCOM","MU","ARM",
        "SMCI","PLTR","SNOW","CRM","ADBE","ORCL","SHOP",
    ]
    JP_CORE = [
        "7203.T","6758.T","9984.T","8035.T","6954.T","4063.T","7735.T","6920.T","6857.T",
        "4523.T","6501.T","9432.T","9433.T","9434.T","2914.T","4502.T","3382.T",
        "8306.T","8316.T","8411.T","8591.T",
    ]
    base = sorted(set(US_CORE + JP_CORE))
    if extra:
        base = sorted(set(base + [x.strip() for x in extra if x.strip()]))
    return base

def ai_universe(extra_ai=None):
    US_AI = ["NVDA","AMD","AVGO","MSFT","GOOGL","META","AMZN","TSM","ASML","ARM","PLTR","SNOW","SMCI","CRM","ADBE"]
    JP_AI = ["8035.T","6920.T","6857.T","7735.T","9984.T","6758.T","4063.T","6526.T","6619.T"]
    base = sorted(set(US_AI + JP_AI))
    if extra_ai:
        base = sorted(set(base + [x.strip() for x in extra_ai if x.strip()]))
    return base

def split_universe(extra=None):
    allu = master_universe(extra)
    aiu  = ai_universe()
    non_ai = sorted([t for t in allu if t not in set(aiu)])
    only_ai = sorted([t for t in aiu if t in set(allu) or '.' in t or t.isupper()])
    return non_ai, only_ai
