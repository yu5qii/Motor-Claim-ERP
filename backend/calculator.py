from datetime import date, datetime

def vehicle_age(reg_date, asof=None):
    if not reg_date:
        return None
    asof = asof or date.today()
    years = asof.year - reg_date.year
    months = asof.month - reg_date.month
    days = asof.day - reg_date.day
    if days < 0:
        months -= 1
    if months < 0:
        years -= 1
        months += 12
    return years, months

def metal_dep(years, months):
    age = years + months/12.0
    if age <= 0.5: return 0
    if age <= 1: return 5
    if age <= 2: return 10
    if age <= 3: return 15
    if age <= 4: return 25
    if age <= 5: return 35
    if age <= 10: return 40
    return 50

def depreciation_for_row(row, metal_rate):
    pmg = str(row.get("PMG","")).upper()
    if pmg == "M": return metal_rate
    if pmg == "P": return 50
    if pmg == "G": return 0
    return 0
