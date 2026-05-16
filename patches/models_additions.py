# ==================== ОСТАТКИ И ПРОДАЖИ ====================

class StockBalance(db.Model):
    __tablename__ = 'stock_balances'
    id = db.Column(db.Integer, primary_key=True)
    
    sbis_nomenclature_id = db.Column(db.String(100), index=True)
    sbis_warehouse_id = db.Column(db.String(100))
    
    name = db.Column(db.String(500))
    normalized_name = db.Column(db.String(500), index=True)
    
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(50))
    
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=True)
    ingredient = db.relationship('Ingredient', backref='stock_balances')
    
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('sbis_nomenclature_id', 'sbis_warehouse_id', name='uix_stock_balance'),
    )

class SaleRecord(db.Model):
    __tablename__ = 'sale_records'
    id = db.Column(db.Integer, primary_key=True)
    
    sbis_order_id = db.Column(db.String(100), unique=True, index=True)
    order_number = db.Column(db.String(100))
    
    date = db.Column(db.DateTime)
    point_id = db.Column(db.String(100))
    
    total_sum = db.Column(db.Float)
    total_sum_with_vat = db.Column(db.Float)
    
    status = db.Column(db.String(50))
    items_json = db.Column(db.JSON)
    
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

class DailySalesSummary(db.Model):
    __tablename__ = 'daily_sales_summary'
    id = db.Column(db.Integer, primary_key=True)
    
    date = db.Column(db.Date, unique=True, index=True)
    
    total_orders = db.Column(db.Integer, default=0)
    total_sum = db.Column(db.Float, default=0)
    total_sum_with_vat = db.Column(db.Float, default=0)
    beer_sales = db.Column(db.Float, default=0)
    food_sales = db.Column(db.Float, default=0)
    
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
