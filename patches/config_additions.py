    # SBIS Retail IDs (заполните свои)
    SBIS_POINT_ID = os.environ.get('SBIS_POINT_ID') or ''
    SBIS_WAREHOUSE_ID = os.environ.get('SBIS_WAREHOUSE_ID') or ''
    SBIS_COMPANY_ID = os.environ.get('SBIS_COMPANY_ID') or ''
    SBIS_PRICE_LIST_ID = os.environ.get('SBIS_PRICE_LIST_ID') or ''
    
    # Business logic
    ESTIMATED_MONTHLY_SALES = int(os.environ.get('ESTIMATED_MONTHLY_SALES', 1000))
