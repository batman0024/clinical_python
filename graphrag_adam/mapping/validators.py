

def validate_required_columns(df, required):
    missing = [c for c in required if c not in df.columns]
    return missing
