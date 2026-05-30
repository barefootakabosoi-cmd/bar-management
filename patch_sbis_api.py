# ДОБАВИТЬ В КОНЕЦ КЛАССА SbisAPI В ФАЙЛЕ sbis_api.py
# (перед строкой "class SbisRetailAPI")

    # ========== DOCOPENING / АКТСПИСАНИЯ / ДОКОТГРИСХ ==========

    def get_doc_openings(self, start_date, end_date):
        """Получает список DocOpening (вскрытие кег)"""
        return self.get_documents('DocOpening', start_date, end_date)

    def get_writeoffs(self, start_date, end_date):
        """Получает список АктСписания"""
        return self.get_documents('АктСписания', start_date, end_date)

    def get_sales_docs(self, start_date, end_date):
        """Получает список ДокОтгрИсх (розничные продажи)"""
        return self.get_documents('ДокОтгрИсх', start_date, end_date)

    def get_doc_items_from_attachment(self, doc_id, doc_type):
        """Получает номенклатуру из ВложениеУчета (XML)"""
        doc = self.get_document(doc_id, doc_type)
        if not doc or 'ВложениеУчета' not in doc:
            return []

        attachments = doc['ВложениеУчета']
        if not attachments or 'Файл' not in attachments[0]:
            return []

        file_url = attachments[0]['Файл'].get('Ссылка')
        if not file_url:
            return []

        try:
            resp = requests.get(file_url, headers=self.headers, timeout=30)
            if resp.status_code != 200:
                return []

            xml_text = resp.text

            if doc_type == 'ДокОтгрИсх':
                return self._parse_upd_xml(xml_text)
            else:
                return self._parse_act_xml(xml_text)
        except Exception as e:
            print(f"Error downloading attachment: {e}")
            return []

    def get_doc_relations(self, doc_id, doc_type):
        """Получает связи документа (основания и следствия)"""
        doc = self.get_document(doc_id, doc_type)
        if not doc:
            return {'base': [], 'consequence': []}

        result = {'base': [], 'consequence': []}

        if 'ДокументОснование' in doc:
            for item in doc['ДокументОснование']:
                d = item.get('Документ', {})
                result['base'].append({
                    'type': d.get('Тип'),
                    'number': d.get('Номер'),
                    'date': d.get('Дата'),
                    'id': d.get('Идентификатор')
                })

        if 'ДокументСледствие' in doc:
            for item in doc['ДокументСледствие']:
                d = item.get('Документ', {})
                result['consequence'].append({
                    'type': d.get('Тип'),
                    'number': d.get('Номер'),
                    'date': d.get('Дата'),
                    'id': d.get('Идентификатор')
                })

        return result

    def _parse_act_xml(self, xml_text):
        """Парсит XML Акта/DocOpening (ТаблТовар)"""
        import xml.etree.ElementTree as ET
        items = []
        try:
            root = ET.fromstring(xml_text)
            for doc in root.iter('Документ'):
                for tabl in doc.iter('ТаблТовар'):
                    for row in tabl.iter('СтрТабл'):
                        item = {
                            'name': row.get('Наименование', ''),
                            'quantity': float(row.get('Количество', 0) or 0),
                            'unit': row.get('ЕдИзм', ''),
                            'price': float(row.get('Цена', 0) or 0),
                            'sum': float(row.get('Сумма', 0) or 0),
                            'sku': row.get('НомНомер', ''),
                            'gtin': row.get('ГТИН', ''),
                            'alc_code': ''
                        }
                        for param in row.iter('Параметр'):
                            if param.get('Имя') == 'AlcCode':
                                item['alc_code'] = param.get('Значение', '')
                        items.append(item)
        except Exception as e:
            print(f"Act XML parse error: {e}")
        return items

    def _parse_upd_xml(self, xml_text):
        """Парсит УПД (ДокОтгрИсх) — ТаблСчФакт"""
        import xml.etree.ElementTree as ET
        items = []
        try:
            root = ET.fromstring(xml_text)
            for doc in root.iter('Документ'):
                for tabl in doc.iter('ТаблСчФакт'):
                    for row in tabl.iter('СведТов'):
                        items.append({
                            'name': row.get('НаимТов', ''),
                            'quantity': float(row.get('КолТов', 0) or 0),
                            'unit': row.get('НаимЕдИзм', ''),
                            'price': float(row.get('ЦенаТов', 0) or 0),
                            'sum': float(row.get('СтТовБезНДС', 0) or 0),
                            'sku': '', 'gtin': '', 'alc_code': ''
                        })
        except Exception as e:
            print(f"UPD XML parse error: {e}")
        return items
