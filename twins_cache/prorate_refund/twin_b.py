# model: gemini/gemini-3-flash-preview
# prompt_sha256: a7f280c0d46490accfae019f16a9031d15566696be0cc5ca5f553f079acd1a1b
# generated_utc: 2026-11-07T23:39:56Z
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

def prorate_refund(price: str, period_start: str, period_end: str, cancel_date: str) -> str:
    """
    Refund the unused part of a billing period when a customer cancels.
    Iterates day by day to calculate total and used days.
    """
    # Validate price
    try:
        d_price = Decimal(price)
    except Exception:
        raise ValueError("Malformed price string.")
    
    if d_price < 0:
        raise ValueError("Price cannot be negative.")
    
    # Check for more than 2 decimal places in the price string
    if "." in price:
        if len(price.split(".")[1]) > 2:
            raise ValueError("Price cannot have more than 2 decimal places.")
            
    # Validate dates
    try:
        d_start = date.fromisoformat(period_start)
        d_end = date.fromisoformat(period_end)
        d_cancel = date.fromisoformat(cancel_date)
    except Exception:
        raise ValueError("Malformed date string.")
        
    if d_end <= d_start:
        raise ValueError("period_end must be after period_start.")
        
    # Rule 3: cancel_date on or after period_end
    if d_cancel >= d_end:
        return "0.00"
        
    # Rule 4: cancel_date before period_start
    if d_cancel < d_start:
        return format(d_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f")
        
    # Rule 1: Calculate total_days by iterating day by day
    total_days = 0
    curr = d_start
    while curr < d_end:
        total_days += 1
        curr += timedelta(days=1)
        
    # Rule 5: Calculate used_days by iterating day by day
    used_days = 0
    curr = d_start
    while curr <= d_cancel and curr < d_end:
        used_days += 1
        curr += timedelta(days=1)
        
    # Rule 5: unused_days = total_days - used_days
    unused_days = total_days - used_days
    
    # Rule 6: refund = price * unused_days / total_days
    # Use Decimal for high precision arithmetic before rounding
    refund = (d_price * Decimal(unused_days)) / Decimal(total_days)
    
    # Round to nearest cent, exact halves rounded up
    refund_rounded = refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    # Return as decimal string with exactly 2 decimal places
    return format(refund_rounded, ".2f")
