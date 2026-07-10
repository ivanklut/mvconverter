"""
Модуль markvan/aggregator.py
Аналитический цех Ядра Маркван (Пост-процессинг дерева).
Выполняет сборку оглавлений, сносок и раскрывает ленивые переменные {{key}}

"""

from markvan.models import (
	Document, Section, Inclusion
)
from utils import ptlog as pt
from utils import makeslug

import os
from utils.makeslug import make_slug




def process_document_aggregations(doc: Document):
	"""
	УНИВЕРСАЛЬНЫЙ КАCКАДНЫЙ СБОРЩИК ДОКУМЕНТА (KISS).
	Перебирает ноды один раз, собирает банк сносок и выгружает по зонам жизни.
	"""
	all_sections = []
	all_nodes = []
	_flatten_document(doc.body, all_sections, all_nodes)
	
	
	# Считаем явные блоки автора
	count_ftncollectblock  = sum(1 for n in all_nodes if n.__class__.__name__ == "FootnotesCollectionBlock")
	explicit_blocks_rendered = 0
	
	# Единый банк текстов сносок всей главы для защиты от капризов стека
	chapter_footnote_texts = []
	current_footnotes_accumulator = []
	

		
	# === ВЫЧИСЛЯЕМ ЗРЯЧИЙ АТРИБУТ ТЕКУЩЕЙ ПАПКИ (Твой новый канон) ===
	dir_slug = getattr(doc, 'dir_slug', '')
	
	# Первичный сбор слагов для мешка уникальных ассетов
	collected_slugs = set(link.slug_path for link in doc.linked_assets if hasattr(link, 'slug_path'))
	
	auto_footnote_counter = 0
	metadata = getattr(doc, 'metadata', {})

	# Переменные-указатели для каскада сносок по секциям
	last_level_1_section = None
	last_level_2_section = None

	# === ЭТАП А: Выгребаем все FootnoteAttach из карманов абсолютно всех нод ===
	# не помню нафига это нужно, тем более в отдельном цикле
	for node in all_nodes:
		if hasattr(node, 'attachments') and node.attachments:
			for att in list(node.attachments):
				if att.__class__.__name__ == 'FootnoteAttach':
					chapter_footnote_texts.append(att)
					node.attachments.remove(att)

	# === ЭТАП Б: 
	for node in all_nodes:
		class_name = node.__class__.__name__
		


		# --- 1. Собираем в словарь перечень используемых включений и их классов 
		# для автоматического добавления соответствующих стилей и скриптов в site_templater.py
		# doc.features = {'TableIncl': {'default', 'freeze'},'MediaIncl': {'image'}, ...}
		# Если нода является включением
		if isinstance(node, Inclusion):
			_register_node_feature_assets(doc, node)

		# --- 2. ТЕКСТОВАЯ ПРОЗА ---
		if class_name in ["Paragraph", "ListItem", "Heading"]:
			nodes_inlines = getattr(node, 'inline_elements', None) or getattr(node, 'inlines', [])
			if nodes_inlines:
				# 💎 ТОЧКА 2: СКАН ИНЛАЙНОВ НА НАЛИЧИЕ СТРОЧНЫХ ТЕХ-ВКЛЮЧЕНИЙ
				# =============================================================
				for el in nodes_inlines:
					if el and el.__class__.__name__ == "InlineIncl":
						_register_node_feature_assets(doc, el)
						
				_resolve_inline_variables(nodes_inlines, metadata)
				
				# Строго связываем по нашему банку текстов главы!
				ftn_container = [auto_footnote_counter]
				_bind_footnote_attachments(
					inline_list=nodes_inlines,
					attachments=chapter_footnote_texts, 
					doc_footnotes=current_footnotes_accumulator, 
					auto_counter_ref=ftn_container
				)
				auto_footnote_counter = ftn_container[0]  # Извлекаем чистое число
				
				# 1. Связыватель обычных ссылок Link из кармана attachments
				if hasattr(node, 'attachments') and node.attachments:
					_bind_linkspan_link_attachments(nodes_inlines, node.attachments, [])
					
				# =============================================================
				# ✨ ОПЕРАЦИЯ "ПРОЗРЕНИЕ ССЫЛОК ПРОЗЫ" В ОЗУ (ПЕРЕНЕСЕНА СЮДА!)
				# =============================================================
				# Теперь, когда ВСЕ ссылки (и инлайновые, и концевые из аттачей) 
				# легально пришились к тексту, мы намертво слагофицируем их паспорта!
				for el in nodes_inlines:
					if el.__class__.__name__ == 'LinkSpan' and getattr(el, 'link', None) is not None:
						_normalize_and_slugify_link(el.link, dir_slug)
				# =============================================================
					
				# Сбор download-ассетов (Они уже залетают зрячими!)
				for el in nodes_inlines:
					if el.__class__.__name__ == 'LinkSpan' and getattr(el, 'link', None) is not None:
						link_obj = el.link
						if getattr(link_obj, 'type', '') == 'download':
							slug = getattr(link_obj, 'slug_path', '')
							if slug and not slug.startswith('#') and slug not in collected_slugs:
								doc.linked_assets.append(link_obj)
								collected_slugs.add(slug)


		# --- 3: Медиавключения [[ ]] (Картинки, Галереи, Видео) ---
		elif class_name == "MediaIncl":
			
			# 1. Сшиваем картинки с их вложениями, если они есть
			if hasattr(node, 'items') and node.items and hasattr(node, 'attachments') and node.attachments:
				_bind_mediaincl_link_attachments(items_list=node.items, attachments=node.attachments)
				
			# 2. ШЛЮЗ Б: Тут же собираем саму картинку и ссылку-перехватчик в мешок ассетов
			if getattr(node, 'items', None):
				for item in node.items:
					src_obj = getattr(item, 'src_path', None)
					if src_obj:
						# =====================================================
						# ✨ ОПЕРАЦИЯ "ПРОЗРЕНИЕ КАРТИНКИ ГАЛЕРЕИ" В ОЗУ
						# =====================================================
						_normalize_and_slugify_link(src_obj, dir_slug)
						# =====================================================
						if getattr(src_obj, 'type', '') == 'local':
							src_slug = getattr(src_obj, 'slug_path', '')
							if src_slug and src_slug not in collected_slugs:
								doc.linked_assets.append(src_obj)
								collected_slugs.add(src_slug)

					action_obj = getattr(item, 'action_link', None)
					if action_obj:
						# =====================================================
						# ✨ ОПЕРАЦИЯ "ПРОЗРЕНИЕ ССЫЛКИ-ДЕЙСТВИЯ КАРТИНКИ" В ОЗУ
						# =====================================================
						_normalize_and_slugify_link(action_obj, dir_slug)
						# =====================================================
						if getattr(action_obj, 'type', '') == 'local':
							act_slug = getattr(action_obj, 'slug_path', '')
							if act_slug and act_slug not in collected_slugs:
								doc.linked_assets.append(action_obj)
								collected_slugs.add(act_slug)

		# --- ГРУППА 3: Автонумерация списков (ListBlock) ---
		elif class_name == 'ListBlock':
			
			# Запускаем автонумерацию только для корневых списков
			_resolve_auto_numbering(node, parent_counters=[])

		# --- 2. ЯВНЫЙ БЛOК {§footnotes§} ---
		elif class_name == "FootnotesCollectionBlock":
			node.items = list(current_footnotes_accumulator)			
			current_footnotes_accumulator.clear()
			count_ftncollectblock -= 1

		# --- 3. ГРАНИЦА СЕКЦИЙ (Появление новой Части/Главы/Раздела) ---
		elif class_name == "Section":
			if count_ftncollectblock == 0:
				if current_footnotes_accumulator:
					from markvan.models import FootnotesCollectionBlock
					phantom_block = FootnotesCollectionBlock()
					phantom_block.items = list(current_footnotes_accumulator)
					
					if node.level == 2:
						if last_level_2_section and hasattr(last_level_2_section, 'nodes'):
							last_level_2_section.nodes.append(phantom_block)
						else:
							if node.parent and hasattr(node.parent, 'nodes'):
								node.parent.nodes.append(phantom_block)
							else:
								doc.body.nodes.append(phantom_block)
								
					elif node.level == 1:
						if last_level_2_section and hasattr(last_level_2_section, 'nodes'):
							last_level_2_section.nodes.append(phantom_block)
						elif last_level_1_section and hasattr(last_level_1_section, 'nodes'):
							last_level_1_section.nodes.append(phantom_block)
						else:
							doc.body.nodes.append(phantom_block)
					
					current_footnotes_accumulator.clear()
			
			if node.level == 1:
				last_level_1_section = node
				last_level_2_section = None
			elif node.level == 2:
				last_level_2_section = node

	# === 4. ФИНАЛЬНЫЙ АВТОМАТИЧЕСКИЙ СБРОС В КOНЦЕ ДОКУМЕНТА ===
	if current_footnotes_accumulator:
		from markvan.models import FootnotesCollectionBlock
		phantom_block = FootnotesCollectionBlock()
		phantom_block.items = list(current_footnotes_accumulator)
		doc.body.nodes.append(phantom_block)
		current_footnotes_accumulator.clear()

	# === ЭТАП В: Финальный автовыброс в самый конец файла ===
	if current_footnotes_accumulator:
		from markvan.models import FootnotesCollectionBlock
		phantom_block = FootnotesCollectionBlock()
		phantom_block.items = list(current_footnotes_accumulator)
		doc.body.nodes.append(phantom_block)
		current_footnotes_accumulator.clear()


	#pt.deb(f"🔋 [FEATURES СБОР] Карта ассетов для этой страницы: {getattr(doc, 'features', {})}")

	_generate_table_of_contents(doc, all_sections, all_nodes)
	_resolve_lazy_variables(doc, all_nodes)



# ===
def _register_node_feature_assets(doc, node) -> None:
	"""
	УНИВЕРСАЛЬНЫЙ СБОРЩИК ФИЧ ДЛЯ БИЛДЕРА САЙТА (KISS).
	Принимает ЛЮБУЮ ноду (и блочную Inclusion, и строчную InlineIncl) 
	и регистрирует её CSS/JS паспорта в ОЗУ.
	"""
	if not node:
		return
		
	class_name = node.__class__.__name__
	current_tag = ""
	
	# Кейс А: Это блочное включение (Inclusion), у которого есть готовый node_tag
	if hasattr(node, 'node_tag') and node.node_tag:
		current_tag = node.node_tag
		
	# Кейс Б: Это строчное техническое включение (InlineIncl)
	# Извлекаем его семантический тип (например, 'code', 'math', 'input')
	elif class_name == "InlineIncl" and hasattr(node, 'incl_type') and node.incl_type:
		current_tag = str(node.incl_type).strip().lower()

	# Если семантический тег успешно определён — пакуем класс в мешок!
	if current_tag:
		if current_tag not in doc.features:
			doc.features[current_tag] = set()

		# Вытягиваем модификатор автора (например, 'image', 'rust', 'default')
		# Если у инлайна класс пустой, пишем 'default'
		incl_class = getattr(node, 'incl_class', 'default') or 'default'
		
		# Заливаем в общий сет с автоматической защитой от дубликатов
		doc.features[current_tag].add(str(incl_class).strip().lower())



def _resolve_inline_variables(inline_list: list, metadata: dict) -> None:
	"""
	ПРОЦЕССОР ПЕРЕМЕННЫХ.
	Раскрывает ленивые переменные {{key}} в тексте из глобального паспорта книги [INDEX].
	"""
	from markvan.models import TextSpan, VariableSpan

	for idx, el in enumerate(inline_list):
		if isinstance(el, VariableSpan):
			key_name = el.key.strip()
			if key_name in metadata:
				inline_list[idx] = TextSpan(text=str(metadata[key_name]))
			else:
				inline_list[idx] = TextSpan(text=f"{{{{{key_name}}}}}")
				
		# Рекурсивный спуск в матрешки стилей (жирный, курсив) [INDEX]
		elif hasattr(el, "children") and el.children:
			_resolve_inline_variables(el.children, metadata)





# ===
# Создатели агрегирующих включений

def _generate_table_of_contents(doc: Document, all_sections: list, all_nodes: list):
	"""
	Автоматически наполняет блоки {§toc} заголовками всей книги [INDEX].
	"""
	# Собираем все легальные заголовки книги (пропуская нулевой корень Section(level=0))
	valid_headings = [s for s in all_sections if s.level > 0]
	
	for node in all_nodes:
		if node.__class__.__name__ == 'TableOfContents':
			# Наполняем агрегатор оглавления списком собранных секций [INDEX]!
			node.items = valid_headings


# ===
# Служебные функции

def _flatten_document(section, all_sections, all_nodes):
	"""
	Рекурсивно разворачивает дерево книги в плоскую ленту ОЗУ (KISS).
	Принимает объект Section и выгребает всех детей.
	"""
	if not section or not hasattr(section, 'nodes'):
		return
		
	all_sections.append(section)
	
	for node in section.nodes:
		if not node:
			continue
			
		all_nodes.append(node)
		class_name = node.__class__.__name__
		
		# === Удаляем Маркер пустой ячейки, если он вне группирующего контейнера
		if class_name == "GroupSpacer":
			if section.__class__.__name__ != "GroupingIncl":
				import utils.ptlog as pt
				pt.wrn("Маркер пустой ячейки .[]. обнаружен ВНЕ сетки! Он будет удалён.", "АГРЕГАТОР")
				continue # Просто пропускаем её, не добавляя в плоский список all_nodes!
		# =====================================================================


		# ---------------------------------------------------------------------
		# 1. МАТРЁШКА СЕКЦИЙ (Части, Главы, Подразделы)
		# ---------------------------------------------------------------------
		if class_name == "Section":
			_flatten_document(node, all_sections, all_nodes)
			
		# ---------------------------------------------------------------------
		# 2. МАТРЁШКА КОНТЕКСТНЫХ ПАР (Твой монолитный тандем Предикат + Зависимый)
		# ---------------------------------------------------------------------
		elif class_name == "ContextPair":
			# Создаем зрячий временный прокси-контейнер для детей контекстной пары,
			# чтобы не нарушать контракт рекурсии по section.nodes!
			proxy_sec = Section(level=getattr(section, 'level', 0) + 1)
			proxy_sec.nodes = []
			
			if getattr(node, 'predicate_node', None):
				proxy_sec.nodes.append(node.predicate_node)
			if getattr(node, 'dependent_node', None):
				proxy_sec.nodes.append(node.dependent_node)
				
			if proxy_sec.nodes:
				_flatten_document(proxy_sec, all_sections, all_nodes)

		# ---------------------------------------------------------------------
		# 3. МАТРЁШКА СПИСКОВ (Разворачиваем ListBlock -> ListItem -> sub_items)
		# ---------------------------------------------------------------------
		elif class_name == "ListBlock" and hasattr(node, "items"):
			proxy_sec = Section(level=getattr(section, 'level', 0) + 1)
			proxy_sec.nodes = list(node.items)
			_flatten_document(proxy_sec, all_sections, all_nodes)
			
		elif class_name == "ListItem" and hasattr(node, "sub_items"):
			proxy_sec = Section(level=getattr(section, 'level', 0) + 1)
			proxy_sec.nodes = list(node.sub_items)
			_flatten_document(proxy_sec, all_sections, all_nodes)

		# ---------------------------------------------------------------------
		# 4. МАТРЁШКА БЛОЧНЫХ ВКЛЮЧЕНИЙ [( Текст )]
		# ---------------------------------------------------------------------
		elif class_name == "TextIncl":
			inner_nodes = getattr(node, 'nodes', getattr(getattr(node, 'body', None), 'nodes', []))
			if inner_nodes:
				proxy_sec = Section(level=getattr(section, 'level', 0) + 1)
				proxy_sec.nodes = list(inner_nodes)
				_flatten_document(proxy_sec, all_sections, all_nodes)


def unpack_list_block(list_block_node: object, all_nodes: list) -> None:
	"""
	Вспомогательный потрошитель списков. 
	Раскладывает пункты и вложенную прозу в плоскую ленту.
	"""
	# ТОЧЕЧНОЕ ИСПРАВЛЕНИЕ: Если корневой узел списка еще не добавлен в ленту all_nodes,
	# мы принудительно закидываем его на передовую, чтобы агрегатор нумерации его увидел!
	if list_block_node not in all_nodes:
		all_nodes.append(list_block_node)

	for item in list_block_node.items:
		all_nodes.append(item)
		# Заныриваем в мешок sub_items пункта списка
		if hasattr(item, 'sub_items') and item.sub_items:
			for sub_node in item.sub_items:
				all_nodes.append(sub_node)
				# Рекурсия: если внутри пункта лежит вложенный подсписок — потрошим и его!
				if sub_node.__class__.__name__ == 'ListBlock':
					unpack_list_block(sub_node, all_nodes)


def _resolve_lazy_variables(doc: Document, all_nodes: list):
	"""
	Служебный финальный лоск для подсчета сквозных глобальных метрик книги.
	Проставляет сквозные порядковые номера сноскам, медиа-файлам и собирает статистику.
	"""
	footnote_global_counter = 1
	media_global_counter = 1
	
	total_paragraphs = 0
	total_lists = 0
	
	# Пробегаемся по всей плоской ленте документов книги
	for node in all_nodes:
		node_class = node.__class__.__name__
		
		# # === 1. СБОР СТАТИСТИКИ КНИГИ ===
		# if node_class == 'Paragraph':
		# 	total_paragraphs += 1
		# elif node_class == 'ListBlock':
		# 	total_lists += 1

		# # === 2. СКВОЗНАЯ НУМЕРАЦИЯ МЕДИАВКЛЮЧЕНИЙ ===
		# elif node_class == 'MediaIncl' and hasattr(node, 'items') and node.items:
		# 	for item in node.items:
		# 		# Каждому физическому файлу (картинке/треку) даем уникальный глобальный ID
		# 		item.global_index = media_global_counter
		# 		media_global_counter += 1

		# === 3. СКВОЗНАЯ НУМЕРАЦИЯ ВСЕХ ПОЙМАННЫХ СНОСОК ===
		# Сноски могут лежать в инлайнах абзацев прозы или пунктов списков
		if hasattr(node, 'inlines') and node.inlines:
			# Локальная микро-функция для рекурсивного поиска сносок в матрешках стилей
			def number_footnotes_deep(inlines_list):
				nonlocal footnote_global_counter
				for el in inlines_list:
					if el.__class__.__name__ == 'FootnoteAnchorSpan':
						# Проставляем сноске её честный сквозной номер для рендерера
						el.global_number = footnote_global_counter
						footnote_global_counter += 1
						
					# Заныриваем в матрешки стилей (жирный, курсив, ссылки)
					if hasattr(el, 'children') and el.children:
						number_footnotes_deep(el.children)
					if hasattr(el, 'inline_elements') and el.inline_elements:
						number_footnotes_deep(el.inline_elements)

			number_footnotes_deep(node.inlines)

	# Записываем собранные метрики в общие метаданные документа
	if not hasattr(doc, 'metrics'):
		doc.metrics = {}
		
	doc.metrics['total_paragraphs'] = total_paragraphs
	doc.metrics['total_lists'] = total_lists
	doc.metrics['total_footnotes'] = footnote_global_counter - 1
	doc.metrics['total_media_items'] = media_global_counter - 1



def _bind_linkspan_link_attachments(inline_list: list, attachments: list, footnotes_accumulator: list) -> None:
	"""Связыватель аттачментов."""
	from markvan.models import LinkSpan

	for el in inline_list:
		if isinstance(el, LinkSpan):
			if el.link is None:
				found_idx = -1
				for a_idx, att in enumerate(attachments):
					if att.__class__.__name__ == 'Link':
						found_idx = a_idx
						break
				
				if found_idx != -1:
					el.link = attachments.pop(found_idx)

				else:
					pass


def _bind_mediaincl_link_attachments(items_list: list, attachments: list) -> None:
	"""
	СПЕЦИАЛИЗИРОВАННЫЙ СВЯЗЫВАТЕЛЬ МЕДИАВКЛЮЧЕНИЙ С ТОТАЛЬНЫМ ДЕБАГОМ.
	"""
	for idx, item in enumerate(items_list):
		# Смотрим класс и текущее состояние action_link каждой картинки
		act_link_val = getattr(item, 'action_link', 'ОТСУТСТВУЕТ ПОЛЕ')
		act_link_class = act_link_val.__class__.__name__ if act_link_val is not None else "None"
		
		# === ПРОВЕРКА УСЛОВИЯ ВХОДА ===
		is_none = act_link_val is None
		is_nonetype_str = act_link_class == 'NoneType'
		
		if is_none or is_nonetype_str:
			found_idx = -1

			for a_idx, att in enumerate(attachments):
				att_class = att.__class__.__name__

				if "Link" in att_class:
					found_idx = a_idx
					break
			
			
			if found_idx != -1:
				item.action_link = attachments.pop(found_idx)
			else:
				pass

def _resolve_auto_numbering(list_block_node: object, parent_counters: list = None) -> None:
	"""
	УЛЬТИМАТИВНЫЙ МНОГОУРОВНЕВЫЙ СЧЁТЧИК АВТОНУМЕРАЦИИ.
	Рекурсивно пробегает дерево списков, заменяет '#' и собирает строки: 1., 1.1., 1.1.1.
	"""
	if parent_counters is None:
		parent_counters = []

	# Если это автонумеруемый список, инициализируем локальный счётчик для текущего уровня
	current_counter = 1

	for item in list_block_node.items:


		# Формируем итоговую строку номера для текущего пункта

		if list_block_node.kind == "auto_numbered":
			# Собираем все родительские цифры и добавляем текущую
			current_level_counters = parent_counters + [current_counter]
			
			# Склеиваем их через точки и обязательно добавляем точку в конце по спецификации
			generated_number = ".".join(str(c) for c in current_level_counters) + "."

			# Записываем вычисленный номер в manual_number пункта!
			item.manual_number = generated_number
			
			# Увеличиваем счётчик для следующего соседа на этом же уровне
			current_counter += 1
		else:
			# Если список маркированный или с ручными номерами (1), 
			# мы не трогаем manual_number, но вложенные списки внутри него всё равно должны знать
			# текущий срез номеров. Передаем пустой или родительский срез без инкремента.
			current_level_counters = parent_counters

		# Заныриваем в мешок sub_items пункта списка для поиска вложенных подсписков!
		if hasattr(item, 'sub_items') and item.sub_items:
			for sub_node in item.sub_items:
				if sub_node.__class__.__name__ == 'ListBlock':
					# РЕКУРСИВНЫЙ СТАРТ: уходим на этаж ниже, передавая накопленный стек цифр!
					_resolve_auto_numbering(sub_node, current_level_counters)



# ===
# Новые функции

def _bind_footnote_attachments(inline_list: list, attachments: list, doc_footnotes: list, auto_counter_ref: list) -> None:
	"""
	СТРОГИЙ СВЯЗЫВАТЕЛЬ СНОСОК (KISS).
	"""
	for el in inline_list:
		if el.__class__.__name__ == 'FootnoteSpan':
			if getattr(el, 'footnote_content', None) is None:
				found_idx = -1
				
				# Бежим по банку и ищем строгое совпадение
				for a_idx, att in enumerate(attachments):
					if att.__class__.__name__ == 'FootnoteAttach':
						
						# Автонумерация
						if el.id_type == 'auto' and att.id_type == 'auto':
							found_idx = a_idx
							break
							
						# Символы и Мануальные (СТРОГОЕ совпадение очищенных ID!)
						elif el.id_type == att.id_type:
							v1 = str(getattr(el, 'res_ftn_id', '')).strip()
							v2 = str(getattr(att, 'res_ftn_id', '')).strip()
							if v1 and v2 and v1 == v2:
								found_idx = a_idx
								break

				# Если совпадение железное — связываем
				if found_idx != -1:
					attach_obj = attachments.pop(found_idx)
					
					if el.id_type == 'auto':
						auto_counter_ref[0] += 1
						current_num = str(auto_counter_ref[0])
						el.res_ftn_id = current_num
						attach_obj.res_ftn_id = current_num
					else:
						attach_obj.res_ftn_id = el.res_ftn_id

					el.footnote_content = attach_obj
					doc_footnotes.append(attach_obj)



# ===

def _normalize_and_slugify_link(link_obj, doc_dir_slug: str) -> None:
	if not link_obj:
		return

	# Если ссылка внешняя (http://, https://, почта, внешние протоколы)
	if link_obj.type not in ["local", "download"]:
		# Её слаг-маршрут — это и есть её честный, оригинальный адрес веба!
		link_obj.slug_path = link_obj.address
		link_obj.is_absolute = False
		return

	raw_address = link_obj.address.replace("\\", "/").strip()
	
	if raw_address.startswith("#"):
		link_obj.slug_path = raw_address
		link_obj.is_absolute = False
		return

	is_absolute = raw_address.startswith("/")
	clean_address = raw_address.lstrip("/")

	if is_absolute:
		full_virtual_path = clean_address
		link_obj.is_absolute = True
	else:
		if doc_dir_slug:
			dirty_path = f"{doc_dir_slug}/{clean_address}"
			full_virtual_path = os.path.normpath(dirty_path).replace("\\", "/")
		else:
			full_virtual_path = clean_address
		link_obj.is_absolute = True

	parts = [make_slug(p) for p in full_virtual_path.split("/") if p]
	link_obj.slug_path = "/".join(parts)

