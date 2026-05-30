# ДОБАВИТЬ В КОНЕЦ ФАЙЛА models.py (перед if __name__)

# ========== V8: DocOpening / АктСписания ==========

class KegOpening(db.Model):
    """Вскрытие кеги (DocOpening -> АктСписания)"""
    __tablename__ = 'keg_openings'

    id = db.Column(db.Integer, primary_key=True)
    doc_number = db.Column(db.String(50))
    doc_date = db.Column(db.Date)
    name = db.Column(db.String(500))  # Номенклатура кеги
    quantity = db.Column(db.Float)    # Количество (дкл)
    unit = db.Column(db.String(20))   # дкл
    price = db.Column(db.Float)       # Цена за дкл
    sum = db.Column(db.Float)         # Сумма
    sku = db.Column(db.String(100))
    alc_code = db.Column(db.String(50))
    gtin = db.Column(db.String(50))
    is_mapped = db.Column(db.Boolean, default=False)
    mapped_retail_name = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Writeoff(db.Model):
    """Списания (АктСписания)"""
    __tablename__ = 'writeoffs'

    id = db.Column(db.Integer, primary_key=True)
    doc_number = db.Column(db.String(50))
    doc_date = db.Column(db.Date)
    writeoff_type = db.Column(db.String(50))  # отключение_крана, брак, прочее
    note = db.Column(db.Text)
    name = db.Column(db.String(500))
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))
    price = db.Column(db.Float)
    sum = db.Column(db.Float)
    sku = db.Column(db.String(100))
    alc_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class KegRetailMapping(db.Model):
    """Связь кеги -> розлив"""
    __tablename__ = 'keg_retail_mapping'

    id = db.Column(db.Integer, primary_key=True)
    keg_name = db.Column(db.String(500), unique=True)
    retail_name = db.Column(db.String(500))
    alc_code = db.Column(db.String(50))
    liters_per_keg = db.Column(db.Float, default=30.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
