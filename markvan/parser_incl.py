"""
parser_incl.py
Обработчик многострочных блочных включений [X ... X], {X ... X}.
Самостоятельно собирает включение и обрабатывает его.
Поддерживает неограниченную вложенность блоков друг в друга через счетчик depth.
def parse_inclusion управляет общей обработкой вложения. 
	-> def prepare_inclusion разделяет на большие части
	-> def create_inclusion_node 
		- создаёт объекты включений 
		- запускает соответствующие обработчики тел включений, которые создают свои объекты

"""

from utils import ptlog as pt
from markvan.models import (
	TextIncl, CommentIncl, PreIncl, CodeIncl, FormulaIncl, MediaIncl, MediaItem, 
	GroupingIncl, SpoilerIncl, InputIncl, TableIncl, 
	TableCell, TableRow, TableOfContents, 
	SpoilerCollectionBlock,	GlossaryBlock, FootnotesCollectionBlock,
	RawCodeBlock
)
from markvan import parser_lines
from markvan import parser

# ===
# Перечень маркеров для def parse_inclusion

INCLUSION_PAIRS = {
	'[(': ')]',  # Блоки-матрешки текста
	'[/': '/]',  # Комментарии 
	'[`': '`]',  # Преформатированный текст
	'[&': '&]',  # Код
	'[%': '%]',  # Формулы
	'[[': ']]',  # Медиа
	'[|': '|]',  # Табличные матрицы
	'[.': '.]',  # Группировки
	'[_': '_]',  # Спойлеры
	'[$': '$]',  # Блок интерактивного ввода данных
	'{&': '&}',  # Инъекция
	'{§': '§}',  # Динамические блоки агрегации (TOC, сноски)
}
# Словарь умолчаний и сокращений классов блочных включений.
MARKVAN_CLASS_ALIASES = {
	'[(': {

		# Информационные блоки
		'i': 'note',
		
		# Сигнальные акценты
		'!': 'important',
		't': 'tip',
		'f': 'fact',
		
		# Экспертные рубежи и предупреждения
		'*': 'advice',
		'!!': 'warning',
		'!!!': 'danger',
		
		# Литературные формы
		'"': 'quote',
		'e': 'epigraph',
		
		# Учебные и проверочные блоки
		'?': 'quest',
		'>': 'answer',
		'=': 'result',
		
		# Констатация результатов тестирования
		'=v': 'success',
		'=x': 'fail'
	},
	'[/': {
		'!': 'todo',
		'?': 'issue',		
	},
		'[[': {
		'': 'image',	
		'img': 'image',
		'pic': 'pictogram',
	},
	'[|': {
		# '': 'default'
	}
}

def parse_inclusion(lines: list[str], line_num: int, stack: list, open_marker: str) -> int:
	"""
	Главный диспетчер обработки включений.
	"""
	close_marker = INCLUSION_PAIRS.get(open_marker, '?]')
	meta_marker = '###' if open_marker == '[(' else ''
	# Сразу определяем строку начального маркера включения
	first_line = lines[line_num].strip()
	

	# === ШАГ 1. Подготовитель собирает тело включения и метаданные за один проход (рекурсия)
	body_lines, content_meta, last_line, next_line_idx = prepare_inclusion(
		lines, line_num, open_marker, close_marker, meta_marker
	)
	# Если подготовитель вернул пустую последнюю строку — значит, маркер закрытия не обнаружен.
	if last_line == "":
		pt.wrn(f"Ошибка разметки! Включение '{open_marker}' не имеет закрывающего маркера '{close_marker}' до конца файла!", first_line)
		return line_num + 1

	# === ШАГ 2. Аналитик вычленяет комментарии и общие параметры включения
	block_attr = {"id": "", "class": "", "title": "", "description": ""}

	# --- А. Парсим строку начального маркера включения
	clean_first_line, _, comment_raw_text1 = parser_lines.prepare_line(first_line)	
	words = clean_first_line.split()
	
	# 1. Находим класс.
	incl_class_raw = words[0][len(open_marker):]
	incl_class_raw = incl_class_raw.strip().lower() 
	# Нормализуем сокращения классов	
	incl_class = MARKVAN_CLASS_ALIASES.get(open_marker, {}).get(incl_class_raw, incl_class_raw)
	if not incl_class:
		incl_class = "default"
	block_attr["class"] = incl_class

	# 2. Ищем идентификатор.
	title_words_start_idx = 1
	if len(words) >= 2:
		title_words_start_idx = 1 # Возможно заголовок начнется со 2-го слова.
		# Проверим второе на наличие идентификатора.
		if words[1].startswith('#'):
				block_attr["id"] = words[1][1:]
				title_words_start_idx = 2 # Заголовок начнется со 3-го слова.
					
	# 3. Всё, что осталось после разбора параметров, склеиваем в Title.
	block_attr["title"] = " ".join(words[title_words_start_idx:])

	# --- Б. Парсим строку конечного маркера включения
	clean_last_line= last_line.strip()[len(close_marker):]

	last_text, _, comment_raw_text2 = parser_lines.prepare_line(clean_last_line)
	# 1. Ищем описание
	block_attr["description"] = last_text

	# === Шаг 3. Создаем объект включения
	incl_node = create_inclusion_node(open_marker, block_attr, body_lines, content_meta)
	
	if incl_node is not None:
		if comment_raw_text1:
			incl_node.comments.append(comment_raw_text1)
		if comment_raw_text2:
			incl_node.comments.append(comment_raw_text2)

	# === Шаг 4. Выгрузка объектов в стек
	if incl_node is not None:
		# Сначала кладем саму ноду включения
		stack[-1].nodes.append(incl_node)

	return next_line_idx





def prepare_inclusion(lines: list[str], line_num: int, open_marker: str, close_marker: str, meta_marker: str = '') -> tuple[list[str], list[str], str, int]:
	"""
	ИНТЕЛЛЕКТУАЛЬНЫЙ ОДНОПРОХОДНЫЙ СБОРЩИК МАРКВАНА [INDEX].
	Рассчитывает баланс вложенности маркеров, защищая матрешки от преждевременного закрытия [INDEX]!
	"""
	body_lines = []
	content_meta = []
	last_line = ""
	
	scan_idx = line_num + 1 
	total_lines = len(lines)
	
	# Счётчик глубины вложенности. Мы уже внутри первого блока, так что стартуем с 1 [INDEX]
	nesting_level = 1
	is_inside_meta_zone = False
	
	while scan_idx < total_lines:
		current_line = lines[scan_idx]
		clean_l = current_line.strip()
		
		# СЦЕНАРИЙ А: Автор открыл ЕЩЕ ОДНУ вложенную матрешку внутри текущей! [INDEX]
		# (Ищем именно чистый двухсимвольный open_marker, например, '[(')
		if open_marker == clean_l[:2] and not clean_l.startswith(close_marker):
			nesting_level += 1
			body_lines.append(current_line)
			scan_idx += 1
			continue
			
		# СЦЕНАРИЙ Б: Поймали закрывающий маркер [INDEX]
		if close_marker == clean_l[:2]:
			nesting_level -= 1
			
			# Если баланс обнулился — ура, это ИСТИННЫЙ финал внешней матрешки [INDEX]!
			if nesting_level == 0:
				last_line = current_line
				scan_idx += 1
				break
			else:
				# Если уровень еще > 0, значит это закрылась внутренняя матрешка. 
				# Просто забираем строку в контент и копаем дальше [INDEX]!
				body_lines.append(current_line)
				scan_idx += 1
				continue
				
		# СЦЕНАРИЙ В: Переключатель метазоны настроек контента ### [INDEX]
		if meta_marker and clean_l == meta_marker:
			is_inside_meta_zone = True
			scan_idx += 1
			continue
			
		# РАСПРЕДЕЛЕНИЕ ТРУДА
		if is_inside_meta_zone:
			content_meta.append(current_line)
		else:
			body_lines.append(current_line)
			
		scan_idx += 1
	return body_lines, content_meta, last_line, scan_idx


def extract_inclusion_metadata(body_lines: list[str], open_marker: str, outer_description: str) -> tuple[dict, dict]:
	"""
	ЭТАП 3: АНАЛИТИК МЕТАДАННЫХ.
	Строго по твоей концепции: первая строка — паспорт, ### — мета контента, хвост — описание [INDEX]!
	"""
	block_attr = {"id": None, "class": None, "title": "", "description": outer_description}
	content_meta = {} # Метаданные самого контента (из зоны ###) [INDEX]
	
	# if not body_lines:
	# 	return block_attr, content_meta
		
	# 1. ПАРСИМ СТАРТОВЫЙ ПАСПОРТ (Самая первая строка блока)
	first_line = body_lines[0].strip()
	# Отрезаем открывающий маркер (например, '[(')
	passport_payload = first_line[len(open_marker):].strip()
	
	# Твой регулярный парсер паспорта вытаскивает Класс, #Идентификатор и Наименование (title) [INDEX]
	# Пример: "Классика #story-1 Легенда о Маркване"
	if passport_payload:
		# (Сюда встаёт твой чистый код нарезки первой строки)
		# block_attr["class"] = ...
		# block_attr["id"] = ...
		# block_attr["title"] = ...
		pass
		
	# Выкидываем строку паспорта из тела контента, чтобы она не пошла в печать [INDEX]
	body_lines.pop(0)
	
	# 2. ТВОЙ МАНЕВР: ИЩЕМ ВНУТРЕННЮЮ ЗОНУ МЕТАДАННЫХ КОНТЕНТА ### [INDEX]
	idx = 0
	while idx < len(body_lines):
		if body_lines[idx].strip() == "###":
			# Всё, что ниже "###" — это служебная мета контента (например, настройки для TextIncl) [INDEX]
			meta_slice = body_lines[idx+1:]
			for m_line in meta_slice:
				if ":" in m_line:
					k, v = m_line.split(":", 1)
					content_meta[k.strip()] = v.strip()
			
			# Отрезаем технический аппендикс ### из тела контента навсегда! [INDEX]
			body_lines[:] = body_lines[:idx]
			break
		idx += 1
		
	return block_attr, content_meta



def create_inclusion_node(open_marker: str, block_attr: dict, body_lines: list[str], content_meta: list[str]) -> object:
	"""
	ЭТАП 4: ФАБРИКА НОД (ЧИСТЫЙ СЛЕПОЙ СБОРЩИК ОБЪЕКТОВ) [INDEX].
	Принимает очищенные мешки данных и плоский список настроек content_meta [INDEX].
	"""
	# Распаковываем базовый паспорт Inclusion для конструкторов классов
	args = {
		"id_": block_attr["id"],
		"incl_class": block_attr["class"],
		"title": block_attr["title"],
		"description": block_attr["description"]
	}
	incl_node = None

	# === ГРУППА 1: УМНЫЕ БЛОКИ-МАТРЕШКИ ===
	if open_marker == '[(':

		incl_node = TextIncl(**args)
		local_stack = [incl_node]
		parser.parse_body(body_lines, local_stack)
		
	elif open_marker == '[.':
		incl_node = GroupingIncl(**args)
		local_stack = [incl_node]
		parser.parse_body(body_lines, local_stack)
		
	elif open_marker == '[_':
		incl_node = SpoilerIncl(**args)

		local_stack = [incl_node]
		parser.parse_body(body_lines, local_stack)

	elif open_marker == '[/':
		incl_node = CommentIncl(**args)
		local_stack = [incl_node]
		# Запускаем рекурсивный построчный парсер Ядра! 
		# Теперь внутри комментария будут полноценные параграфы и списки!
		parser.parse_body(body_lines, local_stack)

	# === ГРУППА 2: СТАТИЧЕСКИЕ ТЕХ-ВКЛЮЧЕНИЯ ===
	elif open_marker == '[`':
		incl_node = PreIncl(**args)
		incl_node.raw_lines = body_lines

	elif open_marker == '[&':
		incl_node = CodeIncl(**args)
		incl_node.raw_lines = body_lines

	elif open_marker == '[%':
		incl_node = FormulaIncl(**args)
		incl_node.raw_lines = body_lines	

	elif open_marker == '[[':
		incl_node = MediaIncl(**args)
		parse_media_body(body_lines, incl_node)

	elif open_marker == '[|':
		#if args["incl_class"] == "none": args["incl_class"] = "basic"
		incl_node = TableIncl(**args)
		# Твой отлаженный табличный процессор наполняет ноду данными!
		parse_table_body(body_lines, incl_node)

	# === ГРУППА 3
	elif open_marker == '[$':
		incl_node = InputIncl(**args)
		incl_node.raw_lines = body_lines

	# === ГРУППА 4: ДИНАМИЧЕСКИЕ БЛОКИ АГРЕГАЦИИ (ОБЪЕКТЫ EMBED) ===
	elif open_marker == '{§':
		# Выуживаем лимиты из твоего нового плоского списка настроек content_meta!
		# Напишем быстрый линейный поиск, так как это теперь плоский массив строк
		limit_val = "all"
		sort_val = "chronology"
		
		for m_line in content_meta:
			clean_m = m_line.strip()
			if clean_m.startswith("limit:"):
				limit_val = clean_m.split(":", 1)[1].strip()
			elif clean_m.startswith("sort:"):
				sort_val = clean_m.split(":", 1)[1].strip()
		
		# Проверяем имя коллекции прямо из поля Класса
		collection_type = block_attr["class"]
		
		if collection_type == "toc":
			incl_node = TableOfContents(**args)
			incl_node.limit_level = limit_val
		elif collection_type == "spoiler":
			incl_node = SpoilerCollectionBlock(**args)
			incl_node.limit_level = limit_val
		elif collection_type == "glossary":
			incl_node = GlossaryBlock(**args)
			# Складываем метаданные сортировки в словарь ноды
			incl_node.internal_meta["sort"] = sort_val 
		elif collection_type == "footnotes":
			incl_node = FootnotesCollectionBlock(**args)

	# === ГРУППА 5: ПРЯМАЯ ИНЪЕКЦИЯ КОДА ===
	elif open_marker == '{&':
		incl_node = RawCodeBlock(**args)
		incl_node.raw_lines = body_lines

	# === ЕДИНЫЙ МЕХАНИЗМ СОХРАНЕНИЯ МЕТАДАННЫХ КОНТЕНТА ===
	if incl_node is not None:
		# Сохраняем плоский список строк из зоны ### прямо в ноду контента! [INDEX]
		incl_node.content_meta_lines = content_meta

	return incl_node




# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Функции обработки типов ключений

def parse_table_body(body_lines: list[str], table_node) -> None:
	"""
	Функция парсинга тела таблицы внутри parser_incl.py.
	Наполняет семантическую ноду TableIncl строками и ячейками в памяти .
	"""
	table_head = []
	table_body = []
	table_foot = []
	table_temp = []
	row_temp = []
	
	colspan = 2
	row_num = 0
	col_num = 0
		
	abbr_class = {
		'': 'basic', 
		'=': 'total', 
		'#': 'number', 
		'<': 'stub',
		'!': 'attent'
	}
	
	for line in body_lines:
		clean_l = line.strip()
		if len(clean_l) == 0:
			continue

		# Разделители зон тегов по твоему канону
		if clean_l.startswith('---'):
			if row_temp: table_temp.append(row_temp)
			table_head = table_temp
			table_temp, row_temp = [], []
			row_num = 0
			continue

		if clean_l.startswith('==='):
			if row_temp: table_temp.append(row_temp)
			table_body = table_temp
			table_temp, row_temp = [], []
			row_num = 0
			continue

		# Вычисляем маркер начала строки
		# Новая строка таблицы начинается, если clean_l СТАРТУЕТ с палочки или точки! [INDEX]
		row_begin = line.startswith('|') or line.startswith('.')
		
		if row_begin and row_temp:			
			table_temp.append(row_temp)
			row_temp = []
			colspan = 2
			row_num += 1
			col_num = 0

		# Создаем объект нашей новой чистой ячейки Марквана
		cell = TableCell()
		#marker = clean_l

		if clean_l.startswith('|') or clean_l.startswith('!'):
			# Запоминаем, какой именно маркер открыл ячейку
			start_marker = clean_l[0]
			
			# Вытаскиваем символ стиля ячейки (он идет строго на индексе 1) [INDEX]
			cls_char = clean_l[1] if len(clean_l) > 1 else ''
			
			# Задаем базовый класс в зависимости от стартового маркера [INDEX]
			# Если стартанули с '!', базовый класс — attent, иначе basic [INDEX]
			base_class = 'attent' if start_marker == '!' else 'basic'
			
			# Если на индексе 1 сидит модификатор (# или =), берем его класс, иначе base_class [INDEX]
			# Но еще круче — если там модификатор, мы склеиваем классы через пробел! (Например: "attent number") [INDEX]
			if cls_char in abbr_class and cls_char != '':
				if start_marker == '!':
					cell.css_class = f"attent {abbr_class[cls_char]}" # И акцент, и число/итог одновременно [INDEX]!
				else:
					cell.css_class = abbr_class[cls_char]
			else:
				cell.css_class = base_class
			
			# Вычисляем, с какого индекса идет живой текст автора [INDEX]
			start_text_idx = 2 if cls_char in abbr_class and cls_char != '' else 1
			cell.text = clean_l[start_text_idx:].strip()
			
			cell.inlines = parser_lines.parse_textline(cell.text)
			row_temp.append(cell)
			colspan = 2
			col_num += 1

		elif clean_l.startswith(':'):
			cell.is_phantom = True
			# Обратный цикл влево: ищем живую ячейку для colspan
			for i in range(len(row_temp)-1, -1, -1):
				if not row_temp[i].is_phantom:
					row_temp[i].colspan = colspan
					break
			row_temp.append(cell)
			colspan += 1
			
		elif clean_l.startswith('.'):
			cell.is_phantom = True
			row_temp.append(cell)
			# Вертикальный цикл вверх: ищем живую ячейку для rowspan
			for r in range(row_num-1, -1, -1):
				if col_num < len(table_temp[r]):
					target_cell = table_temp[r][col_num]
					if not target_cell.is_phantom:
						target_cell.rowspan += 1
						break
						
		else:
			# СЦЕНАРИЙ ДЕФОЛТА (case _): Склеиваем многострочную висячую строку по твоему правилу!
			# (Например, строка "Для школьников младших классов")
			if row_temp:
				last_cell = row_temp[-1]
				last_cell.text = last_cell.text + '\n' + clean_l
				# Пересобираем инлайны для обновленного многострочного текста
				last_cell.inlines = parser_lines.parse_textline(last_cell.text)

		col_num += 1

	# Смываем остатки в буфер
	if row_temp:
		table_temp.append(row_temp)

	if table_body and table_temp:
		table_foot = table_temp
	else:
		table_body = table_temp

	# =====================================================================
	# === УЛЬТИМАТИВНЫЙ ГEОМEТРИЧEСКИЙ КАЛЬКУЛЯТOР МАТРИЦЫ MARKVAN V3 ===
	# =====================================================================
	# Работает на чистых физических координатах по канонам W3C и Chromium!
	# Идеально рассчитывает любые слияния (colspan/rowspan) в шапке, теле и подвале.
	
	for current_zone in [table_head, table_body, table_foot]:
		max_rows = len(current_zone)
		if max_rows <= 1:
			continue  # Если в зоне всего одна строка, спаны выравнивать нечего
			
		# Шаг 1: Вычисляем максимальную ширину физической сетки (кол-во колонок)
		max_cols = 0
		for row_cells in current_zone:
			total_cols = sum(getattr(c, 'colspan', 1) for c in row_cells)
			if total_cols > max_cols:
				max_cols = total_cols
				
		# Строим пустую координатную карту занятости сетки [ряд][колонка]
		# Изначально вся матрица заполнена значениями None (абсолютно свободно)
		grid_map = [[None for _ in range(max_cols)] for _ in range(max_rows)]

		# Шаг 2: ВОЛНОВОЕ РАСПРЕДЕЛЕНИЕ ЯЧЕЕК ПО КООРДИНАТНОЙ КАРТЕ
		# Бежим строго по рядам сверху вниз
		for r_idx, row_cells in enumerate(current_zone):
			c_phys = 0  # Маркер текущей физической колонки
			
			for cell in row_cells:
				if getattr(cell, 'is_phantom', False):
					continue
					
				# КРИТИЧEСКИЙ СДВИГ: Ищем на текущем ряду самую ПEРВУЮ свободную клетку матрицы!
				# Если эта координата уже занята (например, на неё сверху наехал rowspan соседа),
				# мы просто сдвигаем маркер вправо, пока не найдем абсолютную пустоту!
				while c_phys < max_cols and grid_map[r_idx][c_phys] is not None:
					c_phys += 1
					
				if c_phys >= max_cols:
					break  # Страховка от вылета за границы матрицы
					
				# МЫ НАШЛИ ЧЕСТНУЮ ФИЗИЧЕСКУЮ КООРДИНАТУ ДЛЯ ЯЧЕЙКИ!
				cell._phys_col = c_phys  # Намертво впекаем индекс колонки в объект ноды AST
				
				# Извлекаем параметры слияния ячейки, которые заложил твой парсер
				c_span = getattr(cell, 'colspan', 1)
				r_span = getattr(cell, 'rowspan', 1)
				
				# Бронируем прямоугольную область (colspan × rowspan) на нашей карте занятости!
				for dr in range(r_span):
					for dc in range(c_span):
						if r_idx + dr < max_rows and c_phys + dc < max_cols:
							# Если клетка ещё не занята другими — резервируем её под текущую ячейку
							if grid_map[r_idx + dr][c_phys + dc] is None:
								grid_map[r_idx + dr][c_phys + dc] = cell
								
				# Шаг вправо на ширину текущей ячейки (готовимся к следующей ячейке этого ряда)
				c_phys += c_span

		# Шаг 3: АВТОМАТИЧЕСКИЙ РАСЧЁТ ПУСТУЮЩИХ ХВОСТОВ (Rowspan-дотяжка)
		# Бежим по ячейкам САМОГО ПЕРВОГО РЯДА этой зоны
		for cell in current_zone[0]:
			if getattr(cell, 'is_phantom', False):
				continue
				
			c_start = getattr(cell, '_phys_col', None)
			if c_start is not None:
				c_span = getattr(cell, 'colspan', 1)
				
				# Если у ячейки первого ряда нет горизонтального слияния (она одиночная)
				if c_span == 1:
					needed_rowspan = 1
					# Бежим вертикально вниз по той же самой физической колонке карты занятости
					for next_r in range(1, max_rows):
						# Если на нижних этажах эта клетка осталась девственно пустой (None) —
						# значит, автор просто сократил строку, и ячейка обязана растянуться вниз!
						if grid_map[next_r][c_start] is None:
							needed_rowspan += 1
							grid_map[next_r][c_start] = cell # Помечаем, что её занял наш rowspan
						else:
							# Упёрлись в реальный контент соседа на нижнем этаже — стоп растягивание!
							break
							
					# Перезаписываем честный, законный rowspan на уровне AST-дерева!
					if needed_rowspan > getattr(cell, 'rowspan', 1):
						cell.rowspan = needed_rowspan

	# =====================================================================
	# УПАКОВКА В ОБЪЕКТЫ TABLE-ROW (Твой неизменённый код!)
	# =====================================================================
	for row_cells in table_head:
		row_obj = TableRow()
		row_obj.cells = row_cells
		table_node.thead_rows.append(row_obj)
		
	for row_cells in table_body:
		row_obj = TableRow()
		row_obj.cells = row_cells
		table_node.tbody_rows.append(row_obj)
		
	for row_cells in table_foot:
		row_obj = TableRow()
		row_obj.cells = row_cells
		table_node.tfoot_rows.append(row_obj)





def parse_media_body(body_lines: list[str], media_incl: MediaIncl):
	"""
	Парсер тела медиавключения [[ … ]].
	"""
	
	for line in body_lines:
		_, src_path_obj, comment_obj = parser_lines.prepare_line(line)
		if src_path_obj:
			# Рождаем элемент медиаконтента.
			media_item = MediaItem(src_path=src_path_obj)
			media_incl.items.append(media_item)

		if comment_obj:
			# Сохраняем комментарий.
			media_incl.comments.append(comment_obj)
