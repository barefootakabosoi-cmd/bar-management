from app import app
from sbis_api import create_sbis_api_from_config
from models import db, SBISDocument, SBISDocumentItem
from datetime import datetime
import time

with app.app_context():
    sbis = create_sbis_api_from_config(app.config)
    
    # Получаем все документы
    docs = sbis.get_documents('ДокОтгрВх', days_back=365, page_size=50)
    print(f'\nНачинаем обработку {len(docs)} документов...')
    
    processed = 0
    errors = 0
    skipped = 0
    total_items = 0
    
    for i, doc_summary in enumerate(docs):
        doc_id = doc_summary.get('Идентификатор', '')
        doc_number = doc_summary.get('Номер', '?')
        
        if not doc_id:
            continue
        
        # Проверяем, есть ли уже документ с позициями
        existing = SBISDocument.query.filter_by(sbis_id=doc_id).first()
        if existing and SBISDocumentItem.query.filter_by(document_id=existing.id).count() > 0:
            skipped += 1
            continue
        
        print(f'[{i+1}/{len(docs)}] #{doc_number}')
        
        try:
            from app import _process_sbis_document
            details = sbis.get_document_details(doc_id)
            if details:
                _process_sbis_document(details)
                if existing:
                    items = SBISDocumentItem.query.filter_by(document_id=existing.id).count()
                else:
                    doc = SBISDocument.query.filter_by(sbis_id=doc_id).first()
                    items = SBISDocumentItem.query.filter_by(document_id=doc.id).count() if doc else 0
                
                total_items += items
                processed += 1
                print(f'  OK {items} позиций')
            else:
                print(f'  FAIL Нет данных')
                errors += 1
        except Exception as e:
            print(f'  FAIL {e}')
            errors += 1
        
        # Пауза, чтобы не перегрузить API
        time.sleep(0.3)
    
    print(f'\n=== ГОТОВО ===')
    print(f'Обработано: {processed}')
    print(f'Пропущено (уже есть): {skipped}')
    print(f'Ошибок: {errors}')
    print(f'Всего позиций: {total_items}')
    print(f'Всего документов в БД: {SBISDocument.query.count()}')
    print(f'Всего позиций в БД: {SBISDocumentItem.query.count()}')
