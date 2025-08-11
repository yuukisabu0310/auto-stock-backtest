import random

def stratify_country(tickers):
    jp, us = [], []
    for t in tickers:
        (jp if t.endswith(".T") else us).append(t)
    return {"JP": jp, "US": us}

def stratified_sample(tickers:list, size:int, seed=None):
    if seed is not None:
        random.seed(seed)
    strata = stratify_country(tickers)
    picked = []
    # 交互に層からピック→足りない分は全体から
    while len(picked) < size and any(strata.values()):
        for key in list(strata.keys()):
            group = strata[key]
            if group:
                t = group.pop(random.randrange(len(group)))
                if t not in picked:
                    picked.append(t)
                if len(picked) >= size:
                    break
        else:
            break
    rest_pool = [t for group in strata.values() for t in group if t not in picked]
    random.shuffle(rest_pool)
    need = max(0, size - len(picked))
    picked.extend(rest_pool[:need])
    return picked[:size]
