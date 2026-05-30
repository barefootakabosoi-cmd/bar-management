# ДОБАВИТЬ В КОНЕЦ app.py (перед if __name__ == '__main__')

# ========== V8: DocOpening / АктСписания / ДокОтгрИсх ==========

@app.route('/v8/openings')
@login_required
def v8_openings():
    """Вскрытия кег (DocOpening)"""
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = KegOpening.query.filter(KegOpening.doc_date.between(start, end)).order_by(KegOpening.doc_date.desc()).all()
    return render_template('v8_openings.html', items=items, start=start, end=end)

@app.route('/v8/writeoffs')
@login_required
def v8_writeoffs():
    """Списания (АктСписания)"""
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = Writeoff.query.filter(Writeoff.doc_date.between(start, end)).order_by(Writeoff.doc_date.desc()).all()
    return render_template('v8_writeoffs.html', items=items, start=start, end=end)

@app.route('/v8/sales-docs')
@login_required
def v8_sales_docs():
    """Розничные продажи (ДокОтгрИсх)"""
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = SBISDocumentItem.query.join(SBISDocument).filter(
        SBISDocument.doc_type == 'ДокОтгрИсх',
        SBISDocument.doc_date.between(start, end)
    ).order_by(SBISDocument.doc_date.desc()).all()
    return render_template('v8_sales_docs.html', items=items, start=start, end=end)

@app.route('/v8/sync-docs', methods=['POST'])
@login_required
def v8_sync_docs():
    """Синхронизация DocOpening, АктСписания, ДокОтгрИсх"""
    try:
        api = SbisAPI()
        if not api.authenticate():
            # Пробуем через sbis_retail_api
            from sbis_retail_api import SbisRetailAPI
            api = SbisRetailAPI(
                token=Config.SBIS_TOKEN,
                client_id=Config.SBIS_CLIENT_ID,
                app_secret=Config.SBIS_APP_SECRET,
                secret_key=Config.SBIS_SECRET_KEY
            )
            api.authenticate()
            # Используем его headers
            api.headers = {'X-SBISAccessToken': api.token, 'Content-Type': 'application/json'}

        days = request.form.get('days', 30, type=int)
        end = datetime.now()
        start = end - timedelta(days=days)

        results = {}

        # 1. DocOpening
        openings = api.get_doc_openings(start, end)
        for op in openings:
            op_id = op['Идентификатор']
            rels = api.get_doc_relations(op_id, 'DocOpening')
            items = []
            for cons in rels['consequence']:
                if cons['type'] == 'АктСписания':
                    items = api.get_doc_items_from_attachment(cons['id'], 'АктСписания')
                    break
            for item in items:
                ko = KegOpening(
                    doc_number=op.get('Номер'),
                    doc_date=datetime.strptime(op.get('Дата', ''), '%d.%m.%Y') if op.get('Дата') else None,
                    name=item['name'], quantity=item['quantity'], unit=item['unit'],
                    price=item['price'], sum=item['sum'], sku=item.get('sku', ''),
                    alc_code=item.get('alc_code', ''), gtin=item.get('gtin', '')
                )
                db.session.add(ko)
        results['openings'] = len(openings)

        # 2. АктСписания
        writeoffs = api.get_writeoffs(start, end)
        for doc in writeoffs:
            doc_id = doc['Идентификатор']
            note = doc.get('Примечание', '')
            wtype = 'прочее'
            if 'отключении' in note.lower() or 'крана' in note.lower():
                wtype = 'отключение_крана'
            elif 'брак' in note.lower():
                wtype = 'брак'
            items = api.get_doc_items_from_attachment(doc_id, 'АктСписания')
            for item in items:
                wo = Writeoff(
                    doc_number=doc.get('Номер'),
                    doc_date=datetime.strptime(doc.get('Дата', ''), '%d.%m.%Y') if doc.get('Дата') else None,
                    writeoff_type=wtype, note=note,
                    name=item['name'], quantity=item['quantity'], unit=item['unit'],
                    price=item['price'], sum=item['sum'],
                    sku=item.get('sku', ''), alc_code=item.get('alc_code', '')
                )
                db.session.add(wo)
        results['writeoffs'] = len(writeoffs)

        db.session.commit()
        flash(f"Синхронизировано: {results}", 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка синхронизации: {str(e)}", 'danger')

    return redirect(url_for('v8_openings'))

@app.route('/v8/map-keg', methods=['POST'])
@login_required
def v8_map_keg():
    """Связать кегу с розливом"""
    keg_name = request.form['keg_name']
    retail_name = request.form['retail_name']

    mapping = KegRetailMapping.query.filter_by(keg_name=keg_name).first()
    if not mapping:
        mapping = KegRetailMapping(keg_name=keg_name, retail_name=retail_name)
        db.session.add(mapping)
    else:
        mapping.retail_name = retail_name

    # Обновляем keg_openings
    KegOpening.query.filter_by(name=keg_name).update({
        'is_mapped': True,
        'mapped_retail_name': retail_name
    })

    db.session.commit()
    flash(f"Кега '{keg_name}' связана с '{retail_name}'", 'success')
    return redirect(url_for('v8_openings'))
