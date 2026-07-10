"""
Анализатор сырых текстовых строк. 
Выявляет термины, контекстные пары и обычные абзацы.
"""

import re

from utils import ptlog as pt

from markvan.models import ( InlineElement,CommentInline, 
LinkSpan, InlineIncl, VariableSpan, FootnoteSpan, TextSpan, StyledSpan,
Link
)




# ===
# Перечень маркеров для def parse_textline

# Ссылки и сноски
ANCHOR_MARKERS = {
	r'<\[': ('link', r'\]>'),
	r'\[\*': ('footnote', r'\]')
}


# Строчные включения
INLINE_INCL_MARKERS = {
	r'\{\{': ('variable', r'\}\}'), # Это не совсемстрочное включение: для вставки переменной
	r'``': ('pre', r'``'),  # Это не совсем строчное включение: преформатированный код
	r'&\[': ('code', r'\]&'),
	r'%\[': ('math', r'\]%'),
	r'\$\[': ('input', r'\]\$'),
	r'_\[': ('spoiler', r'\]_'),

}

# Обычные стили (поддерживают вложенность)
STYLE_MARKERS = {
	r'\*\*': 'bold',
	r'~~': 'italic',
	r'~_': 'small',
	r'~\^': 'large',
	r'\^\^': 'sup',
	r'__': 'sub',
	r'-\*': 'term_mention',
	r'!-': 'deleted',
	r'!\+': 'added',
	r'~-': 'foreign'
}

# Зеркальные закрывашки для стилей
STYLE_CLOSERS = {
	'bold': r'\*\*',
	'italic': r'~~',
	'small': r'_\~',
	'large': r'\^~',
	'sup': r'\^\^',
	'sub': r'__',
	'term_mention': r'\*-',
	'deleted': r'-\!',
	'added': r'\+\!',
	'foreign': r'-~'
}

def parse_textline(text: str) -> list[InlineElement]:
	"""
	Парсер строки.
	Разделяет строку на элементы и создаёт список объектов, с соблюдением вложенности

	"""
	if not text:
		return []

	# === Сит 1. Поиск и обработка комментариев и внутристрочных ссылок.
	resulting_nodes = []

	# Выделяем внутристрочные ссылки |> и комментарий ///
	clean_text, link_obj, comment_obj = prepare_line(text)

	if link_obj:
		# 1. Рождаем визуальную ноду-оболочку и передаем ей наш объект Link
		link_span = LinkSpan(link=link_obj)

		# 2. Парсим внутренности текста (жирный, курсив, инлайн-код)
		# Результат рекурсии складываем в дочерние элементы нашей ссылки
		link_span.inline_elements = parse_textline(clean_text)
		
		# 3. Основным результатом этой строки становится именно этот LinkSpan
		resulting_nodes.append(link_span)

		# 4. Если к строке был прикреплен комментарий — дописываем его.
		if comment_obj:
			resulting_nodes.append(comment_obj) 
			
		# Так как концевая ссылка оборачивает ВСЮ строку, на этом парсинг строки окончен
		return resulting_nodes

	# === Сит 2. Обработка чистой строки (вне ссылки)

	# Шаг А: Подготавливаем части строки с помощью регулярных выражений
	nodes_in_line = []
	current_pos = 0
	total_len = len(clean_text)
	
	all_patterns = list(STYLE_MARKERS.keys()) + list(INLINE_INCL_MARKERS.keys()) + list(ANCHOR_MARKERS.keys())
	master_regex = re.compile('|'.join(f'({p})' for p in all_patterns))

	# Шаг Б: Идём по строке 
	while current_pos < total_len:
		match = master_regex.search(clean_text, current_pos)
		
		if not match:
			nodes_in_line.append(TextSpan(text=clean_text[current_pos:]))
			break

		start_idx = match.start()
		if start_idx > current_pos:
			nodes_in_line.append(TextSpan(text=clean_text[current_pos:start_idx]))

		matched_marker = match.group(0)
		next_pos = match.end()

		# --- ВЕТКА Б1: Гиперссылки<[ ... ]>
		if matched_marker == '<[':
			# Ищем закрывающую угловую скобку ']' в остатке строки
			close_match = re.search(r'\]\>', clean_text[next_pos:])
			if close_match:
				actual_end = next_pos + close_match.start()
				raw_content = clean_text[next_pos:actual_end]
				
				# 1. Создаем объект LinkSpan. Так как ссылки еще нет, передаем link=None
				link_span = LinkSpan(link=None)
				
				# 2. Прогоняем внутренний текст через parse_textline, 
				# чтобы там обработались жирный/курсив/сноски
				link_span.inline_elements = parse_textline(raw_content)
				
				# 3. Укладываем готовый инлайн-элемент в общую кучку нод строки
				nodes_in_line.append(link_span)
				
				current_pos = next_pos + close_match.end()
				continue
			else:
				# Если автор забыл закрыть скобку — возвращаем маркер как обычный текст
				nodes_in_line.append(TextSpan(text=matched_marker))
				current_pos = next_pos
				continue

		# --- ВЕТКА Б2: Указатели сносок [* ... ]
		elif matched_marker == '[*':
			# Ищем закрывающую квадратную скобку ']'
			close_match = re.search(r'\]', clean_text[next_pos:])
			if close_match:
				actual_end = next_pos + close_match.start()
				truncated_id = clean_text[next_pos:actual_end].strip()
				
				# =====================================================================
				# РАСКОДИРОВАНИЕ ТИПА ИДЕНТИФИКАТОРА ИНЛАЙН-СНОСКИ (KISS)
				# =====================================================================
				if truncated_id == '#':
					# Сценарий 1: Динамическая автонумерация ([*#])
					id_type = 'auto'
					res_ftn_id = None  # Вычислит агрегатор документа на Шаге 4
					
				elif truncated_id.isdigit():
					# Сценарий 2: Конкретная мануальная цифра автора ([*1], [*2])
					id_type = 'manual'
					res_ftn_id = truncated_id  # Цифра известна сразу, сохраняем её
					
				else:
					# Сценарий 3: Чисто символьный режим ([*], [**], [***])
					id_type = 'symbol'
					res_ftn_id  = '*' + truncated_id

				# Создаём объект ссылки на сноску по твоей утверждённой ООП-модели
				footnote_marker_span = FootnoteSpan(id_type=id_type)

				# Переносим вычисленное/дефолтное значение текстового маркера
				footnote_marker_span.res_ftn_id = res_ftn_id
				
				nodes_in_line.append(footnote_marker_span)
				
				current_pos = next_pos + close_match.end()
				continue
			else:
				nodes_in_line.append(TextSpan(text=matched_marker))
				current_pos = next_pos
				continue


		# --- ВЕТКА Б3: Строчные включения
		raw_key = None
		for k in INLINE_INCL_MARKERS.keys():
			# Убираем экранирующие слэши из ключа для прямого сравнения с matched_marker
			if k.replace('\\', '') == matched_marker:
				raw_key = k
				break

		if raw_key:
			incl_type, closer_str = INLINE_INCL_MARKERS[raw_key]
			clean_closer = closer_str.replace('\\', '')
			
			close_idx = clean_text.find(clean_closer, next_pos)
			if close_idx == -1 and incl_type == 'comment':
				close_idx = total_len
				
			if close_idx != -1:
				raw_content = clean_text[next_pos:close_idx]
				end_pos = close_idx + len(clean_closer)
				incl_class = None
				
				if incl_type not in ['variable', 'comment']:
					class_match = re.match(r'^[a-zA-Z0-9_-]+', clean_text[end_pos:])
					if class_match:
						incl_class = class_match.group(0)
						end_pos += class_match.end()
				
				if incl_type == 'variable':
					nodes_in_line.append(VariableSpan(key=raw_content.strip()))
				# elif incl_type == 'comment':
				# 	nodes_in_line.append(CommentInline(kind='note', text=raw_content.strip()))
				# elif incl_type =='spoiler':
				# 	nodes_in_line.append(SpoilerInline(text=raw_content.strip()))
				else:
					nodes_in_line.append(InlineIncl(incl_type=incl_type, text=raw_content, incl_class=incl_class))
					
				current_pos = end_pos
				continue

		
		# --- ВЕТКА В4: Стили оформления (с поддержкой вложенности)
		style_key = None
		for k in STYLE_MARKERS.keys():
			# Убираем экранирующие слэши из ключа для прямого сравнения с matched_marker
			if k.replace('\\', '') == matched_marker:
				style_key = k
				break

		if style_key:
			style_type = STYLE_MARKERS[style_key]
			closer_regex = STYLE_CLOSERS[style_type]
			
			close_match = re.search(closer_regex, clean_text[next_pos:])
			if close_match:
				actual_start = next_pos + close_match.start()
				inner_text = clean_text[next_pos:actual_start]
				
				style_node = StyledSpan(style_type=style_type)
				# ВНИМАНИЕ: Рекурсивно вызываем обновленную parse_textline!
				style_node.children = parse_textline(inner_text)
				
				nodes_in_line.append(style_node)
				current_pos = next_pos + close_match.end()
				continue
			else:
				nodes_in_line.append(TextSpan(text=matched_marker))
				current_pos = next_pos
				continue

		nodes_in_line.append(TextSpan(text=matched_marker))
		current_pos = next_pos

	if comment_obj:
		nodes_in_line.append(comment_obj)

	return nodes_in_line



# ^^^

def prepare_line(raw_text: str) -> tuple[str, Link | None, CommentInline | None]:
	"""
	Подготовитель строки. 
	Рзделяет строку на 3 части:
	clean_text
	|>> link_raw_text | description_link
	/// comment_raw_text
	Возвращает строку и готовые объекты Link и CommentInline
	"""
	
	# Поиск неэкранированного комментария. 
	# Группа 1 (``.*?``) — «съедает» экранированные блоки, защищая их.
	# Группа 2 (///|//\?|//!) — ловит только свободные маркеры.
	COMMENT_REGEX = re.compile(r'(``.*?``)|(///|//\?|//!)')

	#  Ищеv маркер '|-> '  '|> ' '|>> ' с обязательным пробелом/табом после него
	# ДОБАВЛЯЕМ ВАРИАНТ С ДЕФИСОМ: \->|\|\>\>?
	LINK_PROTECTED_REGEX = re.compile(r'(``.*?``)|(\s*(?:\|\->|\|\>\>?)\s+)(.*)$')


	# ===
	clean_line = raw_text.strip()
	link_raw_text = ""
	comment_raw_text = ""
	
	for match in COMMENT_REGEX.finditer(clean_line):
			# Если совпала Группа 1 — это экранированный текст (например, ``///``), игнорируем его
			if match.group(1):
				continue
				
			# Если совпала Группа 2 — это реальный маркер начала комментария
			if match.group(2):
				marker_start = match.start(2)
				marker = match.group(2)
				
				# Извлекаем текст комментария и сам маркер
				comment_content = clean_line[marker_start + len(marker):].strip()
				comment_raw_text = marker + comment_content
				
				# В чистой строке оставляем ВСЁ, что было до маркера (включая нетронутые бэктики)
				clean_line = clean_line[:marker_start].strip()
				break
			
	comment_obj = parse_comment(comment_raw_text)

	# === ШАГ 2. Получение ссылки с учётом экранирования (Новая умная логика)
	for match in LINK_PROTECTED_REGEX.finditer(clean_line):
		# Если совпала Группа 1 — это экранированный бэктиками блок, игнорируем его и идем дальше
		if match.group(1):
			continue
			
		# Если совпала Группа 2 — мы нашли первый НАСТОЯЩИЙ, неэкранированный маркер ссылки!
		if match.group(2):
			marker_start = match.start(2)
			
			# Забираем всю оригинальную строку автора от начала маркера до самого конца clean_line
			link_raw_text = clean_line[marker_start:].strip()
			
			# В чистой строке оставляем строго всё, что было ДО начала маркера ссылки
			clean_line = clean_line[:marker_start].strip()
			break

	link_obj = parse_link(link_raw_text)

	return clean_line, link_obj, comment_obj


def parse_link(link_raw_text: str) -> Link | None:
	"""
	Парсер сырой строки ссылки.
	Вычисляет тип ('global' или 'local') и раскладывает адрес и описание.
	"""
	if not link_raw_text:
		return None
		
	# Вычисляем тип ссылки на основе маркера
	if link_raw_text.startswith('|->'):
		type = "download"
		marker_len = 3		
	elif link_raw_text.startswith('|>>'):
		type = "global"
		marker_len = 3		
	# И только ЕСЛИ длинные не подошли, проверяем базовый маркер из 2-х символов!
	elif link_raw_text.startswith('|>'):
		type = "local"
		marker_len = 2		
	else:
		# На случай, если прилетела битая строка без маркера
		type = "unknown"
		marker_len = 0

		
	# Отрезаем маркер и чистим пробелы
	payload = link_raw_text[marker_len:].strip()
	
	# Разделяем адрес и описание по вертикальной черте
	if '|' in payload:
		address_part, title_part = payload.split('|', 1)
		address = address_part.strip()
		title = title_part.strip()
	else:
		address = payload
		title = ""
	# Возвращаем твой чистый, классический объект Link
	link_obj = Link(type=type, address=address, title=title)


	return link_obj


def parse_comment(comment_raw_text: str) -> CommentInline | None:
	"""
	Парсер сырой строки комментария.
	Превращает "/// Текст" в объект CommentInline с правильным типом.
	"""
	if not comment_raw_text:
		return None
		
	# Карта маппинга маркеров на типы
	c_class = {"///": "remark", "//?": "issue", "//!": "todo"}
	
	# Извлекаем маркер и чистим текст
	marker = comment_raw_text[:3]
	commen_text = comment_raw_text[3:].strip()
	
	# Получаем понятный тип (дефолт "comment", если что-то пошло не так)
	kind = c_class.get(marker, "")
	
	return CommentInline(kind=kind, text=commen_text)
