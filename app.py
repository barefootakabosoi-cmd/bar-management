from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import json
import pandas as pd
from io import BytesIO

from config import Config
from models import db, Supplier, SupplierOffer, ActiveSupplierPrice, Keg, KegHistory
from models import Recipe, RecipeItem, RecipeVersion, Expense, ExpenseCategory
from models import Bartender, Shift, SBISDocument, SBISDocumentItem, Alert, SyncLog
from models import StockBalance, SaleRecord, DailySalesSummary
from sbis_api import create_sbis_api_from_config, get_last_sync_date

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# ─── INIT ───
@app.before_request
def init_db():
    pass  # Tables created via flask shell or separate script

# ─── DASHBOARD ───
@app.route('/')
def dashboard():
    """Main dashboard with kegs, stats, alerts"""
    # Kegs (16 taps)
    kegs = Keg.query.order_by(Keg.tap_number).all()

    # Ensure we have 16 kegs
    if len(kegs) < 16:
        for i in range(1, 17):
            if not Keg.query.filter_by(tap_number=i).first():
                k = Keg(tap_number=i, status='empty')
                db.session.add(k)
        db.session.commit()
        kegs = Keg.query.order_by(Keg.tap_number).all()

    # Today's purchases
    today = datetime.utcnow().date()
    today_purchases = db.session.query(db.func.sum(SBISDocument.total_amount))\
        .filter(db.func.date(SBISDocument.synced_at) == today).scalar() or 0

    # Monthly profit (simplified)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    # This would integrate with SBIS sales data
    monthly_revenue = 0  # Placeholder

    # Recipe costs
    recipes = Recipe.query.filter_by(status='active').all()

    # Active alerts
    alerts = Alert.query.filter_by(is_read=False).order_by(Alert.created_at.desc()).limit(5).all()
    alert_count = Alert.query.filter_by(is_read=False).count()

    # Promo count
    promo_count = ActiveSupplierPrice.query.filter_by(is_last_promo=True).count()

    # Current shift
    now = datetime.utcnow()
    current_shift = Shift.query.filter(
        Shift.start_time <= now,
        Shift.end_time >= now
    ).first()

    return render_template('dashboard.html',
                         kegs=kegs,
                         today_purchases=today_purchases,
                         monthly_revenue=monthly_revenue,
                         recipes=recipes,
                         alerts=alerts,
                         alert_count=alert_count,
                         promo_count=promo_count,
                         current_shift=current_shift)

# ─── KEGS ───
@app.route('/kegs')
def kegs_list():
    kegs = Keg.query.order_by(Keg.tap_number).all()
    beers = ActiveSupplierPrice.query.filter(
        ActiveSupplierPrice.category.in_(['keg', 'кег']),
        ActiveSupplierPrice.status == 'active'
    ).all()
    return render_template('kegs.html', kegs=kegs, beers=beers)

@app.route('/keg/<int:tap_number>/install', methods=['POST'])
def install_keg(tap_number):
    keg = Keg.query.filter_by(tap_number=tap_number).first_or_404()
    price_id = request.form.get('beer_id')
    volume = float(request.form.get('volume', 30))

    if price_id:
        price = ActiveSupplierPrice.query.get(price_id)
        keg.active_price_id = price_id
        keg.beer_name = price.name
        keg.beer_brand = price.brand

    keg.volume_liters = volume
    keg.remaining_liters = volume
    keg.status = 'active'
    keg.installed_at = datetime.utcnow()
    keg.last_updated = datetime.utcnow()

    db.session.commit()
    flash(f'Кег #{tap_number} установлен: {keg.beer_name}', 'success')
    return redirect(url_for('kegs_list'))

@app.route('/keg/<int:tap_number>/update', methods=['POST'])
def update_keg_level(tap_number):
    keg = Keg.query.filter_by(tap_number=tap_number).first_or_404()
    remaining = float(request.form.get('remaining', keg.remaining_liters))
    keg.remaining_liters = remaining
    keg.last_updated = datetime.utcnow()

    # Auto status
    if remaining <= 0:
        keg.status = 'empty'
    elif remaining <= Config.KEG_LOW_THRESHOLD:
        keg.status = 'low'
    elif remaining <= Config.KEG_WARNING_THRESHOLD:
        keg.status = 'warning'
    else:
        keg.status = 'active'

    db.session.commit()
    return jsonify({'success': True, 'status': keg.status, 'percent': keg.percent_remaining})

# ─── SUPPLIERS ───
@app.route('/suppliers')
def suppliers():
    suppliers = Supplier.query.order_by(Supplier.name).all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/supplier/add', methods=['POST'])
def add_supplier():
    name = request.form.get('name')
    contact = request.form.get('contact')
    email = request.form.get('email')
    phone = request.form.get('phone')

    s = Supplier(name=name, contact=contact, email=email, phone=phone)
    db.session.add(s)
    db.session.commit()
    flash('Поставщик добавлен', 'success')
    return redirect(url_for('suppliers'))

# ─── ACTIVE PRICES ───
@app.route('/prices')
def prices():
    prices = ActiveSupplierPrice.query.order_by(ActiveSupplierPrice.name).all()
    suppliers = Supplier.query.filter_by(status='active').all()
    return render_template('prices.html', prices=prices, suppliers=suppliers)

@app.route('/price/add', methods=['POST'])
def add_price():
    p = ActiveSupplierPrice(
        supplier_id=request.form.get('supplier_id'),
        name=request.form.get('name'),
        category=request.form.get('category'),
        volume=request.form.get('volume'),
        brand=request.form.get('brand'),
        base_price=float(request.form.get('base_price', 0)),
        status=request.form.get('status', 'active')
    )
    db.session.add(p)
    db.session.commit()
    flash('Товар добавлен в каталог', 'success')
    return redirect(url_for('prices'))

@app.route('/price/<int:id>/edit', methods=['POST'])
def edit_price(id):
    p = ActiveSupplierPrice.query.get_or_404(id)
    p.name = request.form.get('name', p.name)
    p.base_price = float(request.form.get('base_price', p.base_price))
    p.status = request.form.get('status', p.status)
    p.last_update = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

# ─── PRICE UPLOAD / OFFERS ───
@app.route('/upload', methods=['GET', 'POST'])
def upload_price():
    if request.method == 'POST':
        file = request.files.get('file')
        supplier_id = request.form.get('supplier_id')

        if file and supplier_id:
            filename = secure_filename(file.filename)
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            file.save(filepath)

            offer = SupplierOffer(
                supplier_id=supplier_id,
                file_name=filename,
                file_path=filepath
            )
            db.session.add(offer)
            db.session.commit()

            # Parse Excel/CSV
            _parse_price_file(offer)

            flash('Прайс загружен и обработан', 'success')
        return redirect(url_for('upload_price'))

    suppliers = Supplier.query.filter_by(status='active').all()
    offers = SupplierOffer.query.order_by(SupplierOffer.uploaded_at.desc()).limit(10).all()
    return render_template('upload_price.html', suppliers=suppliers, offers=offers)

def _parse_price_file(offer):
    """Parse uploaded price file and update active prices"""
    try:
        if offer.file_name.endswith('.xlsx') or offer.file_name.endswith('.xls'):
            df = pd.read_excel(offer.file_path)
        elif offer.file_name.endswith('.csv'):
            df = pd.read_csv(offer.file_path)
        else:
            return

        # Try to detect columns
        name_col = _find_column(df, ['name', 'название', 'наименование', 'товар'])
        price_col = _find_column(df, ['price', 'цена', 'стоимость', 'цена закупки'])

        if not name_col or not price_col:
            return

        items_count = 0
        for _, row in df.iterrows():
            name = str(row.get(name_col, '')).strip()
            price = float(row.get(price_col, 0) or 0)

            if not name or price <= 0:
                continue

            # Find existing or create new
            existing = ActiveSupplierPrice.query.filter(
                ActiveSupplierPrice.supplier_id == offer.supplier_id,
                ActiveSupplierPrice.name.ilike(f'%{name}%')
            ).first()

            if existing:
                # Update if price changed significantly
                old_price = existing.base_price
                existing.base_price = price
                existing.last_update = datetime.utcnow()
                existing.add_price_point(price)

                # Alert on big increase
                if old_price > 0 and price > old_price * 1.1:
                    alert = Alert(
                        type='price_increase',
                        title=f'Цена выросла: {name}',
                        message=f'С {old_price:.0f} ₽ до {price:.0f} ₽ (+{((price-old_price)/old_price*100):.0f}%)',
                        severity='warning',
                        entity_type='price',
                        entity_id=existing.id
                    )
                    db.session.add(alert)
            else:
                new_price = ActiveSupplierPrice(
                    supplier_id=offer.supplier_id,
                    name=name,
                    base_price=price,
                    last_purchase_price=price
                )
                db.session.add(new_price)

            items_count += 1

        offer.items_count = items_count
        offer.processed = True
        db.session.commit()

    except Exception as e:
        print(f"Parse error: {e}")
        offer.processed = False
        db.session.commit()

def _find_column(df, possible_names):
    """Find column by possible names"""
    cols = {c.lower().strip(): c for c in df.columns}
    for name in possible_names:
        if name in cols:
            return cols[name]
    return None

# ─── SBIS SYNC ───
@app.route('/sbis/sync', methods=['POST'])
def sbis_sync():
    """Sync with SBIS — incremental or full"""
    sync_type = request.form.get('sync_type', 'incremental')

    # Log start
    log = SyncLog(sync_type=f'sbis_{sync_type}', status='started')
    db.session.add(log)
    db.session.commit()

    try:
        sbis = create_sbis_api_from_config(app.config)

        # Auth
        if not sbis.token and not sbis.authenticate():
            log.status = 'error'
            log.message = 'Auth failed'
            db.session.commit()
            flash('Ошибка авторизации в СБИС', 'danger')
            return redirect(url_for('dashboard'))

        # Date range
        if sync_type == 'full':
            date_from = datetime.utcnow() - timedelta(days=365)
        else:
            date_from = get_last_sync_date(db)

        date_to = datetime.utcnow()

        # Get existing doc IDs
        existing_ids = {d.sbis_id for d in SBISDocument.query.all()}

        # Sync
        result = sbis.sync_documents(date_from, date_to, existing_ids)

        # Process new documents
        for doc_data in result['new']:
            _process_sbis_document(doc_data)

        # Log success
        log.status = 'success'
        log.items_processed = len(result['new'])
        log.message = f"New: {len(result['new'])}, Errors: {len(result['errors'])}"
        log.completed_at = datetime.utcnow()
        db.session.commit()

        flash(f'Синхронизация завершена. Новых документов: {len(result["new"])}', 'success')

    except Exception as e:
        log.status = 'error'
        log.message = str(e)
        log.completed_at = datetime.utcnow()
        db.session.commit()
        flash(f'Ошибка синхронизации: {e}', 'danger')

    return redirect(url_for('dashboard'))

def _process_sbis_document(doc_data):
    """Process single SBIS document and update prices"""
    # Extract supplier name from Контрагент
    supplier_name = ''
    if 'Контрагент' in doc_data:
        contr = doc_data['Контрагент']
        if 'Название' in contr:
            supplier_name = contr['Название']
        elif 'СвФЛ' in contr and 'НазваниеПолное' in contr['СвФЛ']:
            supplier_name = contr['СвФЛ']['НазваниеПолное']
        elif 'СвЮЛ' in contr and 'НазваниеПолное' in contr['СвЮЛ']:
            supplier_name = contr['СвЮЛ']['НазваниеПолное']
    
    # Find or create supplier
    supplier = None
    if supplier_name:
        supplier = Supplier.query.filter(
            Supplier.name.ilike(f'%{supplier_name}%')
        ).first()
        if not supplier:
            supplier = Supplier(name=supplier_name, status='active')
            db.session.add(supplier)
            db.session.flush()
    
    # Parse date
    doc_date = None
    if 'Дата' in doc_data:
        try:
            doc_date = datetime.strptime(doc_data['Дата'], '%d.%m.%Y')
        except:
            pass
    
    # Parse total amount
    total_amount = 0
    if 'Сумма' in doc_data:
        try:
            total_amount = float(doc_data['Сумма'])
        except:
            pass
    
    sbis_id = doc_data.get('Идентификатор', '')
    
    # === UPSERT: проверяем, есть ли уже такой документ ===
    existing = SBISDocument.query.filter_by(sbis_id=sbis_id).first()
    if existing:
        existing.supplier_id = supplier.id if supplier else existing.supplier_id
        existing.doc_number = doc_data.get('Номер', '')
        existing.doc_date = doc_date
        existing.total_amount = total_amount
        existing.raw_data = json.dumps(doc_data, ensure_ascii=False)
        existing.synced_at = datetime.utcnow()
        db.session.commit()
        print(f"Updated existing doc: {existing.doc_number}")
        
        # Обновляем позиции документа (получаем свежие данные)
        sbis = create_sbis_api_from_config(app.config)
        fresh_doc = sbis.get_document_details(existing.sbis_id)
        items = sbis.get_items_from_upd(fresh_doc if fresh_doc else doc_data)
        if items:
            existing.total_items = len(items)
            # Удаляем старые позиции
            SBISDocumentItem.query.filter_by(document_id=existing.id).delete()
            db.session.commit()
            for item in items:
                processed_item = {
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': item['quantity'],
                    'unit': item.get('unit', 'шт'),
                    'total': item.get('sum', item['price'] * item['quantity'] if item['price'] and item['quantity'] else 0)
                }
                _process_document_item(processed_item, existing.id, supplier)
            db.session.commit()
        return existing
    
    # Create document record (только если не существует)
    doc = SBISDocument(
        sbis_id=sbis_id,
        supplier_id=supplier.id if supplier else None,
        doc_number=doc_data.get('Номер', ''),
        doc_date=doc_date,
        total_amount=total_amount,
        total_items=0,
        raw_data=json.dumps(doc_data, ensure_ascii=False)
    )
    db.session.add(doc)
    db.session.flush()
    
    # Try to get items via XML УПД (новый метод)
    sbis = create_sbis_api_from_config(app.config)
    fresh_doc = sbis.get_document_details(doc_data.get('Идентификатор', ''))
    items = sbis.get_items_from_upd(fresh_doc if fresh_doc else doc_data)
    
    if items:
        doc.total_items = len(items)
        for item in items:
            # Приводим к формату _process_document_item
            processed_item = {
                'name': item['name'],
                'price': item['price'],
                'quantity': item['quantity'],
                'unit': item.get('unit', 'шт'),
                'total': item.get('sum', item['price'] * item['quantity'] if item['price'] and item['quantity'] else 0)
            }
            _process_document_item(processed_item, doc.id, supplier)
    else:
        print(f"No items found in document {doc.doc_number}")
    
    db.session.commit()
    return doc

def _process_document_item(item, doc_id, supplier):
    """Process single item from document — detect promos, update prices"""
    if not supplier:
        return

    # Find active price
    price = ActiveSupplierPrice.query.filter(
        ActiveSupplierPrice.supplier_id == supplier.id,
        ActiveSupplierPrice.name.ilike(f'%{item["name"]}%')
    ).first()

    if not price:
        # Create new active price
        price = ActiveSupplierPrice(
            supplier_id=supplier.id,
            name=item['name'],
            base_price=item['price'],
            last_purchase_price=item['price'],
            category='auto'
        )
        db.session.add(price)
        db.session.flush()

    # Update price
    price.last_purchase_price = item['price']
    price.base_price = item['price']
    price.last_update = datetime.utcnow()

    # Create document item
    doc_item = SBISDocumentItem(
        document_id=doc_id,
        product_name=item['name'],
        quantity=item['quantity'],
        unit=item['unit'],
        price=item['price'],
        total=item['total'],
        active_price_id=price.id
    )
    db.session.add(doc_item)

# ─── RECIPES ───
@app.route('/recipes')
def recipes():
    recipes = Recipe.query.order_by(Recipe.name).all()
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipe/<int:id>')
def recipe_detail(id):
    recipe = Recipe.query.get_or_404(id)
    prices = ActiveSupplierPrice.query.filter_by(status='active').all()
    return render_template('recipe_detail.html', recipe=recipe, prices=prices)

@app.route('/recipe/add', methods=['GET', 'POST'])
def add_recipe():
    if request.method == 'POST':
        r = Recipe(
            name=request.form.get('name'),
            description=request.form.get('description'),
            category=request.form.get('category'),
            portion_size=float(request.form.get('portion_size', 1)),
            portion_unit=request.form.get('portion_unit', 'г'),
            sale_price=float(request.form.get('sale_price', 0))
        )
        db.session.add(r)
        db.session.commit()

        # Save version
        _save_recipe_version(r, "Initial creation")

        flash('Рецепт создан', 'success')
        return redirect(url_for('recipe_detail', id=r.id))

    return render_template('add_recipe.html')

@app.route('/recipe/<int:id>/add_item', methods=['POST'])
def add_recipe_item(id):
    recipe = Recipe.query.get_or_404(id)

    price_id = request.form.get('ingredient_id')
    quantity = float(request.form.get('quantity', 0))
    unit = request.form.get('unit', 'г')

    price = ActiveSupplierPrice.query.get(price_id) if price_id else None

    unit_cost = price.base_price if price else 0
    total_cost = unit_cost * quantity / 1000 if unit == 'г' else unit_cost * quantity

    item = RecipeItem(
        recipe_id=id,
        active_price_id=price_id,
        ingredient_name=price.name if price else request.form.get('ingredient_name'),
        quantity=quantity,
        unit=unit,
        unit_cost=unit_cost,
        total_cost=total_cost
    )
    db.session.add(item)

    # Recalculate recipe cost
    _recalculate_recipe(recipe)

    db.session.commit()
    return redirect(url_for('recipe_detail', id=id))

def _recalculate_recipe(recipe):
    """Recalculate total cost and margin"""
    total = sum(i.total_cost for i in recipe.items)
    recipe.total_cost = total
    if recipe.sale_price > 0:
        recipe.margin_percent = ((recipe.sale_price - total) / recipe.sale_price) * 100
    recipe.updated_at = datetime.utcnow()

def _save_recipe_version(recipe, note):
    """Save recipe snapshot"""
    data = {
        'name': recipe.name,
        'items': [{
            'name': i.ingredient_name,
            'quantity': i.quantity,
            'unit': i.unit,
            'cost': i.unit_cost
        } for i in recipe.items],
        'total_cost': recipe.total_cost,
        'sale_price': recipe.sale_price
    }

    version_num = (RecipeVersion.query.filter_by(recipe_id=recipe.id).count() or 0) + 1

    v = RecipeVersion(
        recipe_id=recipe.id,
        version_number=version_num,
        data_json=json.dumps(data),
        change_note=note
    )
    db.session.add(v)

@app.route('/recipe/<int:id>/pdf')
def recipe_pdf(id):
    """Generate PDF for recipe"""
    recipe = Recipe.query.get_or_404(id)
    # Would use reportlab or similar
    # For now, return JSON
    return jsonify({
        'name': recipe.name,
        'cost': recipe.total_cost,
        'sale_price': recipe.sale_price,
        'margin': recipe.margin_percent,
        'items': [{
            'name': i.ingredient_name,
            'quantity': i.quantity,
            'unit': i.unit,
            'cost': i.total_cost
        } for i in recipe.items]
    })

# ─── EXPENSES ───
@app.route('/expenses')
def expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = ExpenseCategory.query.all()
    return render_template('expenses.html', expenses=expenses, categories=categories)

@app.route('/expense/add', methods=['POST'])
def add_expense():
    e = Expense(
        category_id=request.form.get('category_id'),
        name=request.form.get('name'),
        amount=float(request.form.get('amount', 0)),
        period=request.form.get('period', 'monthly'),
        note=request.form.get('note')
    )
    db.session.add(e)
    db.session.commit()
    flash('Расход добавлен', 'success')
    return redirect(url_for('expenses'))

# ─── BARTENDERS & SHIFTS ───
@app.route('/bartenders')
def bartenders():
    bartenders = Bartender.query.filter_by(status='active').all()
    return render_template('bartenders.html', bartenders=bartenders)

@app.route('/bartender/add', methods=['POST'])
def add_bartender():
    b = Bartender(
        name=request.form.get('name'),
        phone=request.form.get('phone'),
        email=request.form.get('email')
    )
    db.session.add(b)
    db.session.commit()
    flash('Бармен добавлен', 'success')
    return redirect(url_for('bartenders'))

@app.route('/shifts')
def shifts():
    today = datetime.utcnow().date()
    shifts = Shift.query.filter(
        Shift.date >= today - timedelta(days=7)
    ).order_by(Shift.date.desc(), Shift.start_time).all()
    bartenders = Bartender.query.filter_by(status='active').all()
    return render_template('shifts.html', shifts=shifts, bartenders=bartenders)

@app.route('/shift/add', methods=['POST'])
def add_shift():
    date_str = request.form.get('date')
    time_str = request.form.get('start_time')

    start = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    end = start + timedelta(hours=8)  # Default 8-hour shift

    s = Shift(
        bartender_id=request.form.get('bartender_id'),
        start_time=start,
        end_time=end,
        date=start.date(),
        shift_type=request.form.get('shift_type', 'evening')
    )
    db.session.add(s)
    db.session.commit()
    flash('Смена добавлена', 'success')
    return redirect(url_for('shifts'))

# ─── ANALYTICS ───
@app.route('/analytics')
def analytics():
    """Analytics dashboard"""
    # Purchase dynamics
    months = 6
    purchase_data = []

    for i in range(months):
        month_start = (datetime.utcnow() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        total = db.session.query(db.func.sum(SBISDocument.total_amount))\
            .filter(SBISDocument.doc_date >= month_start)\
            .filter(SBISDocument.doc_date <= month_end).scalar() or 0

        purchase_data.append({
            'month': month_start.strftime('%b %Y'),
            'amount': total
        })

    purchase_data.reverse()

    # Top products by purchase volume
    top_products = db.session.query(
        ActiveSupplierPrice.name,
        db.func.sum(SBISDocumentItem.quantity),
        db.func.sum(SBISDocumentItem.total)
    ).join(SBISDocumentItem).group_by(ActiveSupplierPrice.id)\
     .order_by(db.func.sum(SBISDocumentItem.total).desc()).limit(10).all()

    # Promo savings
    promo_savings = db.session.query(db.func.sum(ActiveSupplierPrice.total_savings)).scalar() or 0

    # Recipe margins
    recipe_margins = Recipe.query.filter_by(status='active').all()

    return render_template('analytics.html',
                         purchase_data=purchase_data,
                         top_products=top_products,
                         promo_savings=promo_savings,
                         recipe_margins=recipe_margins)

# ─── ALERTS ───
@app.route('/alerts')
def alerts():
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    return render_template('alerts.html', alerts=alerts)

@app.route('/alert/<int:id>/read', methods=['POST'])
def read_alert(id):
    alert = Alert.query.get_or_404(id)
    alert.is_read = True
    db.session.commit()
    return jsonify({'success': True})

# ─── SEARCH ───
@app.route('/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return render_template('search.html', results=None, query='')

    # Search prices
    prices = ActiveSupplierPrice.query.filter(
        ActiveSupplierPrice.name.ilike(f'%{q}%')
    ).all()

    # Search recipes
    recipes = Recipe.query.filter(
        Recipe.name.ilike(f'%{q}%')
    ).all()

    return render_template('search.html', 
                         results={'prices': prices, 'recipes': recipes},
                         query=q)

# ─── API ENDPOINTS ───
@app.route('/api/kegs')
def api_kegs():
    kegs = Keg.query.order_by(Keg.tap_number).all()
    return jsonify([{
        'tap': k.tap_number,
        'name': k.beer_name,
        'brand': k.beer_brand,
        'remaining': k.remaining_liters,
        'volume': k.volume_liters,
        'percent': round(k.percent_remaining, 1),
        'status': k.status,
        'days_left': k.days_until_empty,
        'is_low': k.is_low
    } for k in kegs])

@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    today = datetime.utcnow().date()

    today_purchases = db.session.query(db.func.sum(SBISDocument.total_amount))\
        .filter(db.func.date(SBISDocument.synced_at) == today).scalar() or 0

    low_kegs = Keg.query.filter(Keg.remaining_liters <= Config.KEG_LOW_THRESHOLD).count()
    promo_count = ActiveSupplierPrice.query.filter_by(is_last_promo=True).count()
    alert_count = Alert.query.filter_by(is_read=False).count()

    return jsonify({
        'today_purchases': today_purchases,
        'low_kegs': low_kegs,
        'promo_count': promo_count,
        'alert_count': alert_count
    })

# ─── INIT DB COMMAND ───
@app.cli.command('init-db')
def init_db_command():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()

        # Create default expense categories
        defaults = [
            ('Электроэнергия', 'fixed', 'revenue'),
            ('Аренда', 'fixed', 'revenue'),
            ('Зарплата', 'fixed', 'revenue'),
            ('Пакеты/упаковка', 'variable', 'revenue'),
            ('Моющие средства', 'variable', 'revenue'),
            ('Вода', 'variable', 'revenue'),
        ]

        for name, type_, method in defaults:
            if not ExpenseCategory.query.filter_by(name=name).first():
                db.session.add(ExpenseCategory(name=name, type=type_, allocation_method=method))

        db.session.commit()
        print('Database initialized')



# ─── SBIS DOCUMENTS ───
@app.route('/sbis')
def sbis_documents():
    """Список документов СБИС"""
    from models import SBISDocument, Supplier
    docs = SBISDocument.query.order_by(SBISDocument.doc_date.desc()).all()
    for d in docs:
        d.supplier = Supplier.query.get(d.supplier_id) if d.supplier_id else None
    return render_template('sbis_documents.html', documents=docs)


@app.route('/sbis/document/<int:id>')
def sbis_document_detail(id):
    """Детали документа СБИС"""
    from models import SBISDocument, SBISDocumentItem, Supplier
    doc = SBISDocument.query.get_or_404(id)
    items = SBISDocumentItem.query.filter_by(document_id=doc.id).all()
    supplier = Supplier.query.get(doc.supplier_id) if doc.supplier_id else None
    return render_template('sbis_document_detail.html', document=doc, items=items, supplier=supplier)


@app.route('/stock')
def stock():
    """Остатки на складе"""
    balances = StockBalance.query.order_by(StockBalance.quantity).all()
    
    totals = {}
    for bal in balances:
        key = bal.name or 'Неизвестно'
        if key not in totals:
            totals[key] = {'total': 0, 'unit': bal.unit or 'шт'}
        totals[key]['total'] += bal.quantity or 0
    
    return render_template('stock.html', balances=balances, totals=totals)
@app.route('/stock/sync', methods=['POST'])
def sync_stock():
    """Синхронизация остатков со СБИС"""
    try:
        sbis = create_sbis_api_from_config(app.config)
        
        balances_data = sbis.get_balances(
            warehouses=[Config.SBIS_WAREHOUSE_ID] if Config.SBIS_WAREHOUSE_ID else None,
            companies=[Config.SBIS_COMPANY_ID] if Config.SBIS_COMPANY_ID else None
        )
        
        if not balances_data:
            flash('Не удалось получить остатки. Проверьте настройки SBIS_*_ID', 'warning')
            return redirect(url_for('stock'))
        
        StockBalance.query.delete()
        
        balances_list = balances_data.get('balances', []) if isinstance(balances_data, dict) else balances_data
        
        for bal_data in balances_list:
            name = bal_data.get('name', bal_data.get('Номенклатура', ''))
            
            balance = StockBalance(
                sbis_nomenclature_id=str(bal_data.get('id', '')),
                sbis_warehouse_id=str(bal_data.get('warehouseId', Config.SBIS_WAREHOUSE_ID or '')),
                name=name,
                normalized_name=name.lower(),
                quantity=float(bal_data.get('quantity', bal_data.get('Количество', 0)) or 0),
                unit=bal_data.get('unit', bal_data.get('Единица', ''))
            )
            db.session.add(balance)
        
        db.session.commit()
        flash(f'Остатки синхронизированы: {len(balances_list)} позиций', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка синхронизации остатков: {str(e)}', 'error')
    
    return redirect(url_for('stock'))

# ==================== ПРОДАЖИ ====================
@app.route('/sales')
def sales():
    """Продажи"""
    page = request.args.get('page', 1, type=int)
    
    pagination = SaleRecord.query.order_by(SaleRecord.date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    daily = DailySalesSummary.query.order_by(DailySalesSummary.date.desc()).limit(30).all()
    
    return render_template('sales.html', pagination=pagination, daily=daily)
@app.route('/sales/sync', methods=['POST'])
def sync_sales():
    """Синхронизация продаж со СБИС"""
    try:
        days = int(request.form.get('days', 7))
        
        sbis = create_sbis_api_from_config(app.config)
        
        orders = sbis.get_sales_by_period(
            point_id=Config.SBIS_POINT_ID if Config.SBIS_POINT_ID else None,
            days=days
        )
        
        if not orders:
            flash('Нет продаж за период или ошибка API', 'warning')
            return redirect(url_for('sales'))
        
        imported = 0
        
        for order_data in orders:
            order_id = str(order_data.get('id', ''))
            if not order_id:
                continue
            
            sale = SaleRecord.query.filter_by(sbis_order_id=order_id).first()
            if not sale:
                sale = SaleRecord(sbis_order_id=order_id)
                db.session.add(sale)
            
            sale.order_number = order_data.get('number', '')
            
            date_str = order_data.get('dateTime', order_data.get('date', ''))
            if date_str:
                try:
                    sale.date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    sale.date = None
            
            sale.point_id = str(order_data.get('pointId', Config.SBIS_POINT_ID or ''))
            sale.total_sum = float(order_data.get('sum', 0) or 0)
            sale.total_sum_with_vat = float(order_data.get('sumWithVat', sale.total_sum) or 0)
            sale.status = order_data.get('status', '')
            sale.items_json = order_data.get('items', order_data.get('products', []))
            
            imported += 1
            
            if imported % 50 == 0:
                db.session.commit()
        
        db.session.commit()
        
        _recalculate_daily_sales()
        
        flash(f'Импортировано {imported} заказов', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка синхронизации продаж: {str(e)}', 'error')
    
    return redirect(url_for('sales'))

def _recalculate_daily_sales():
    """Пересчёт дневных агрегатов продаж"""
    from sqlalchemy import func, cast, Date
    
    DailySalesSummary.query.delete()
    
    daily_data = db.session.query(
        cast(SaleRecord.date, Date).label('sale_date'),
        func.count(SaleRecord.id).label('orders'),
        func.sum(SaleRecord.total_sum).label('total'),
        func.sum(SaleRecord.total_sum_with_vat).label('total_vat')
    ).filter(SaleRecord.date != None).group_by('sale_date').all()
    
    for row in daily_data:
        summary = DailySalesSummary(
            date=row.sale_date,
            total_orders=row.orders or 0,
            total_sum=row.total or 0,
            total_sum_with_vat=row.total_vat or 0
        )
        db.session.add(summary)
    
    db.session.commit()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

# ==================== ОСТАТКИ (КЕГИ) ====================
