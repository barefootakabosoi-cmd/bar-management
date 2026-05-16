from app import app
from sbis_api import create_sbis_api_from_config
from models import db, SBISDocument, SBISDocumentItem
import time
import sys

with app.app_context():
    sbis = create_sbis_api_from_config(app.config)
    
    # Получаем все документы
    docs = sbis.get_documents('ДокОтгрВх', days_back=365, page_size=50)
    print(f'Всего документов: {len(docs)}')
    
    # Фильтруем: только те, у которых нет позиций
    to_process = []
    for d in docs:
        doc_id = d.get('Идентификатор', '')
        existing = SBISDocument.query.filter_by(sbis_id=doc_id).first()
        if not existing or SBISDocumentItem.query.filter_by(document_id=existing.id).count() == 0:
            to_process.append(d)
    
    print(f'Обработать: {len(to_process)}')
    print(f'Уже есть: {len(docs) - len(to_process)}')
    print('Начинаем...\n')
    
    processed = 0
    errors = 0
    total_items = 0
    
    for i, doc_summary in enumerate(to_process):
        doc_id = doc_summary.get('Идентификатор', '')
        doc_number = doc_summary.get('Номер', '?')
        
        # Прогресс
        pct = (i + 1) / len(to_process) * 100
        sys.stdout.write(f'\r[{i+1}/{len(to_process)}] {pct:.1f}% | #{doc_number}...')
        sys.stdout.flush()
        
        try:
            from app import _process_sbis_document
            details = sbis.get_document_details(doc_id)
            if details:
                _process_sbis_document(details)
                existing = SBISDocument.query.filter_by(sbis_id=doc_id).first()
                items = SBISDocumentItem.query.filter_by(document_id=existing.id).count() if existing else 0
                total_items += items
                processed += 1
            else:
                errors += 1
        except Exception as e:
            errors += 1
        
        # Пауза между документами
        time.sleep(0.5)
    
    print(f'\n\n=== ГОТОВО ===')
    print(f'Обработано: {processed}')
    print(f'Ошибок: {errors}')
    print(f'Всего позиций: {total_items}')
    print(f'Документов в БД: {SBISDocument.query.count()}')
    print(f'Позиций в БД: {SBISDocumentItem.query.count()}')
