def format_traffic_size(bytes_size):
    """Convert bytes to a human-readable format."""
    if bytes_size < 1024:
        return f"{bytes_size} bytes"
    elif bytes_size < 1024**2:
        return f"{bytes_size / 1024:.2f} KB"
    elif bytes_size < 1024**3:
        return f"{bytes_size / 1024**2:.2f} MB"
    else:
        return f"{bytes_size / 1024**3:.2f} GB"
    

import re
def parse_uptime(uptime_str):
    """Parse uptime string (like '1h30m45s') into total seconds."""
    total_seconds = 0
    matches = re.findall(r'(\d+)([hms])', uptime_str)

    for value, unit in matches:
        value = int(value)
        if unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        elif unit == 's':
            total_seconds += value

    return total_seconds