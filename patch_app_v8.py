# ========== V8: DocOpening / АктСписания / ДокОтгрИсх ==========

@app.route('/v8/openings')
def v8_openings():
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = KegOpening.query.filter(KegOpening.doc_date.between(start, end)).order_by(KegOpening.doc_date.desc()).all()
    return render_template('v8_openings.html', items=items, start=start, end=end)


@app.route('/v8/writeoffs')
def v8_writeoffs():
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = Writeoff.query.filter(Writeoff.doc_date.between(start, end)).order_by(Writeoff.doc_date.desc()).all()
    return render_template('v8_writeoffs.html', items=items, start=start, end=end)


@app.route('/v8/sales-docs')
def v8_sales_docs():
    start = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    items = SBISDocumentItem.query.join(SBISDocument).filter(
        SBISDocument.doc_type == 'ДокОтгрИсх',
        SBISDocument.doc_date.between(start, end)
    ).order_by(SBISDocument.doc_date.desc()).all()
    return render_template('v8_sales_docs.html', items=items, start=start, end=end)


@app.route('/v8/sync-docs', methods=['POST'])
def v8_sync_docs():
    try:
        sbis = create_sbis_api_from_config(app.config)
        if not sbis.authenticate():
            flash('Ошибка авторизации в СБИС', 'danger')
            return redirect(url_for('v8_openings'))

        days = request.form.get('days', 30, type=int)
        end = datetime.now()
        start = end - timedelta(days=days)

        results = {}

        # 1. DocOpening
        openings = sbis.get_doc_openings(start, end)
        for op in openings:
            op_id = op.get('Идентификатор', '')
            if not op_id:
                continue
            rels = sbis.get_doc_relations(op_id, 'DocOpening')
            items = []
            for cons in rels.get('consequence', []):
                if cons.get('type') == 'АктСписания':
                    items = sbis.get_doc_items_from_attachment(cons.get('id', ''), 'АктСписания')
                    break
            for item in items:
                ko = KegOpening(
                    doc_number=op.get('Номер', ''),
                    doc_date=datetime.strptime(op.get('Дата', ''), '%d.%m.%Y') if op.get('Дата') else None,
                    name=item.get('name', ''),
                    quantity=item.get('quantity', 0),
                    unit=item.get('unit', ''),
                    price=item.get('price', 0),
                    sum=item.get('sum', 0),
                    sku=item.get('sku', ''),
                    alc_code=item.get('alc_code', ''),
                    gtin=item.get('gtin', '')
                )
                db.session.add(ko)
        results['openings'] = len(openings)

        # 2. АктСписания
        writeoffs = sbis.get_writeoffs(start, end)
        for doc in writeoffs:
            doc_id = doc.get('Идентификатор', '')
            if not doc_id:
                continue
            note = doc.get('Примечание', '')
            wtype = 'прочее'
            if 'отключении' in note.lower() or 'крана' in note.lower():
                wtype = 'отключение_крана'
            elif 'брак' in note.lower():
                wtype = 'брак'
            items = sbis.get_doc_items_from_attachment(doc_id, 'АктСписания')
            for item in items:
                wo = Writeoff(
                    doc_number=doc.get('Номер', ''),
                    doc_date=datetime.strptime(doc.get('Дата', ''), '%d.%m.%Y') if doc.get('Дата') else None,
                    writeoff_type=wtype,
                    note=note,
                    name=item.get('name', ''),
                    quantity=item.get('quantity', 0),
                    unit=item.get('unit', ''),
                    price=item.get('price', 0),
                    sum=item.get('sum', 0),
                    sku=item.get('sku', ''),
                    alc_code=item.get('alc_code', '')
                )
                db.session.add(wo)
        results['writeoffs'] = len(writeoffs)

        db.session.commit()
        flash(f"Синхронизировано: открытий {results.get('openings', 0)}, списаний {results.get('writeoffs', 0)}", 'success')

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка синхронизации: {str(e)}", 'danger')

    return redirect(url_for('v8_openings'))


@app.route('/v8/map-keg', methods=['POST'])
def v8_map_keg():
    keg_name = request.form.get('keg_name', '')
    retail_name = request.form.get('retail_name', '')

    if not keg_name or not retail_name:
        flash('Укажите название кеги и розлива', 'warning')
        return redirect(url_for('v8_openings'))

    mapping = KegRetailMapping.query.filter_by(keg_name=keg_name).first()
    if not mapping:
        mapping = KegRetailMapping(keg_name=keg_name, retail_name=retail_name)
        db.session.add(mapping)
    else:
        mapping.retail_name = retail_name

    KegOpening.query.filter_by(name=keg_name).update({
        'is_mapped': True,
        'mapped_retail_name': retail_name
    })

    db.session.commit()
    flash(f"Кега '{keg_name}' связана с '{retail_name}'", 'success')
    return redirect(url_for('v8_openings'))
