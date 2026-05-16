from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

# ─── SUPPLIERS ───
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')  # active, paused, discontinued
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prices = db.relationship('ActiveSupplierPrice', backref='supplier', lazy=True, cascade='all, delete-orphan')
    offers = db.relationship('SupplierOffer', backref='supplier', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('SBISDocument', backref='supplier', lazy=True)

class SupplierOffer(db.Model):
    __tablename__ = 'supplier_offers'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    file_name = db.Column(db.String(300))
    file_path = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    items_count = db.Column(db.Integer, default=0)

# ─── ACTIVE PRICES (working catalog) ───
class ActiveSupplierPrice(db.Model):
    __tablename__ = 'active_supplier_prices'
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)

    # Product info
    name = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(100))  # keg, bottle, can, food, etc
    volume = db.Column(db.String(50))    # 30л, 0.5л, etc
    brand = db.Column(db.String(100))

    # Price fields
    base_price = db.Column(db.Float, default=0)           # Regular price
    last_purchase_price = db.Column(db.Float, default=0)   # Actual last purchase
    is_last_promo = db.Column(db.Boolean, default=False)    # Was last purchase promo?
    promo_discount_percent = db.Column(db.Float, default=0)
    total_savings = db.Column(db.Float, default=0)          # Total saved on promos

    # Status
    status = db.Column(db.String(20), default='active')  # active, trial, discontinued, seasonal, paused
    season_start = db.Column(db.DateTime)
    season_end = db.Column(db.DateTime)

    # History
    price_history = db.Column(db.Text, default='[]')  # JSON array
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_price_history(self):
        try:
            return json.loads(self.price_history)
        except:
            return []

    def add_price_point(self, price, is_promo=False, discount=0):
        history = self.get_price_history()
        history.append({
            'date': datetime.utcnow().isoformat(),
            'price': price,
            'is_promo': is_promo,
            'discount': discount
        })
        # Keep last 50 points
        self.price_history = json.dumps(history[-50:])

# ─── KEGS (16 taps) ───
class Keg(db.Model):
    __tablename__ = 'kegs'
    id = db.Column(db.Integer, primary_key=True)
    tap_number = db.Column(db.Integer, nullable=False, unique=True)  # 1-16

    # Current beer
    active_price_id = db.Column(db.Integer, db.ForeignKey('active_supplier_prices.id'))
    beer_name = db.Column(db.String(300))
    beer_brand = db.Column(db.String(100))

    # Volume tracking
    volume_liters = db.Column(db.Float, default=30)  # Total keg volume
    remaining_liters = db.Column(db.Float, default=30)

    # Status
    status = db.Column(db.String(20), default='full')  # full, active, low, empty, cleaning

    # Dates
    installed_at = db.Column(db.DateTime)
    expected_empty = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    # Consumption rate (liters per day, calculated)
    consumption_rate = db.Column(db.Float, default=0)

    # Relationship
    active_price = db.relationship('ActiveSupplierPrice')

    @property
    def percent_remaining(self):
        if self.volume_liters and self.volume_liters > 0:
            return (self.remaining_liters / self.volume_liters) * 100
        return 0

    @property
    def days_until_empty(self):
        if self.consumption_rate and self.consumption_rate > 0:
            return int(self.remaining_liters / self.consumption_rate)
        return None

    @property
    def is_low(self):
        return self.remaining_liters < 5  # Less than 5 liters

class KegHistory(db.Model):
    __tablename__ = 'keg_history'
    id = db.Column(db.Integer, primary_key=True)
    keg_id = db.Column(db.Integer, db.ForeignKey('kegs.id'))
    beer_name = db.Column(db.String(300))
    volume_start = db.Column(db.Float)
    volume_end = db.Column(db.Float)
    installed_at = db.Column(db.DateTime)
    removed_at = db.Column(db.DateTime)
    duration_days = db.Column(db.Float)

# ─── RECIPES ───
class Recipe(db.Model):
    __tablename__ = 'recipes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # snack, main, etc

    # Portion
    portion_size = db.Column(db.Float, default=1)  # grams or units
    portion_unit = db.Column(db.String(20), default='г')

    # Cost & margin
    total_cost = db.Column(db.Float, default=0)
    sale_price = db.Column(db.Float, default=0)
    margin_percent = db.Column(db.Float, default=0)

    # Status
    status = db.Column(db.String(20), default='active')  # active, seasonal, discontinued

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship('RecipeItem', backref='recipe', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('RecipeVersion', backref='recipe', lazy=True, cascade='all, delete-orphan')

class RecipeItem(db.Model):
    __tablename__ = 'recipe_items'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)

    # Link to active price or manual entry
    active_price_id = db.Column(db.Integer, db.ForeignKey('active_supplier_prices.id'))
    ingredient_name = db.Column(db.String(300), nullable=False)

    # Quantity in recipe
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='г')

    # Cost at time of recipe creation
    unit_cost = db.Column(db.Float, default=0)
    total_cost = db.Column(db.Float, default=0)

    active_price = db.relationship('ActiveSupplierPrice')

class RecipeVersion(db.Model):
    __tablename__ = 'recipe_versions'
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    data_json = db.Column(db.Text)  # Full recipe snapshot
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    change_note = db.Column(db.String(500))

# ─── EXPENSES (hidden costs) ───
class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50))  # fixed, variable
    allocation_method = db.Column(db.String(50), default='revenue')  # revenue, portion, manual

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'))
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), default='monthly')  # daily, weekly, monthly, yearly
    date = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)

    category = db.relationship('ExpenseCategory')

# ─── BARTENDERS & SHIFTS ───
class Bartender(db.Model):
    __tablename__ = 'bartenders'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    shifts = db.relationship('Shift', backref='bartender', lazy=True)

class Shift(db.Model):
    __tablename__ = 'shifts'
    id = db.Column(db.Integer, primary_key=True)
    bartender_id = db.Column(db.Integer, db.ForeignKey('bartenders.id'), nullable=False)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)

    # Shift details
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), default='evening')  # morning, evening, night

    # Revenue tracked during shift (optional, from SBIS)
    revenue = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)

    status = db.Column(db.String(20), default='scheduled')  # scheduled, active, completed

# ─── SBIS DOCUMENTS ───
class SBISDocument(db.Model):
    __tablename__ = 'sbis_documents'
    id = db.Column(db.Integer, primary_key=True)
    sbis_id = db.Column(db.String(100), unique=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))

    doc_type = db.Column(db.String(50))  # incoming, outgoing
    doc_number = db.Column(db.String(100))
    doc_date = db.Column(db.DateTime)

    total_amount = db.Column(db.Float, default=0)
    total_items = db.Column(db.Integer, default=0)

    # Sync info
    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data = db.Column(db.Text)  # JSON

    items = db.relationship('SBISDocumentItem', backref='document', lazy=True, cascade='all, delete-orphan')

class SBISDocumentItem(db.Model):
    __tablename__ = 'sbis_document_items'
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('sbis_documents.id'), nullable=False)

    product_name = db.Column(db.String(300))
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))
    price = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)

    # Link to our catalog
    active_price_id = db.Column(db.Integer, db.ForeignKey('active_supplier_prices.id'))

    active_price = db.relationship('ActiveSupplierPrice')

# ─── ALERTS ───
class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # price_increase, keg_low, promo, stock
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    severity = db.Column(db.String(20), default='info')  # info, warning, danger

    # Link to entity
    entity_type = db.Column(db.String(50))  # keg, price, supplier
    entity_id = db.Column(db.Integer)

    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─── SYNC LOG ───
class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(50))  # sbis_full, sbis_incremental, prices
    status = db.Column(db.String(20))  # started, success, error
    message = db.Column(db.Text)
    items_processed = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
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
    
    # ingredient_id убран — таблицы ingredients нет
    ingredient_name = db.Column(db.String(200))  # название ингредиента для справки
    
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
