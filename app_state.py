
from datetime import date


today = date.today()
last_year = today.replace(year=today.year - 1) #leap year edge case not handle
last_month = today.replace(month=today.month - 1) if today.month > 1 else today.replace(year=today.year - 1, month=12) #leap year edge case not handled #may need further handling for months with fewer days than today