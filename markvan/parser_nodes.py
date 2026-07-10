"""
Сборник функций обрабатывающий большинство нод документа.
"""
from markvan.parser_lines import parse_textline, prepare_line
from utils import ptlog as pt

from markvan.models import (
	Section, Heading, Paragraph, ListBlock, ListItem, 
	TermDef, ContextPair, EndSection, PauseHead, FootnoteAttach, GroupSpacer
)
from markvan import parser, parser_incl
from markvan import parser_lines


def anayz_textline(lines: list[str], line_num: int, stack: list) -> int:
	"""
	Определитель способа обработки строки без явного маркера (Если в parser.parse_body получился TEXT_LINE)
	Определяет тип ноды: термин, контекстная пара или обычный абзац. И создаёт ноду, вызывая соответствующие функции.
	"""
	raw_line = lines[line_num]
	clean_line = raw_line.strip()
	if not clean_line:
		return line_num + 1

	# --- Шаг А: Проверка на семантический термин
	if clean_line.startswith("*-"):

		parts = clean_line.split("-*", 1)
		if len(parts) == 2:
			term_raw = parts[0].replace("*-", "").strip()
			definition_raw = parts[1].strip()

			# 1. Рождаем ноду пары термина и определения
			term_pair_node = TermDef()
			
			# 2. Напрямую заполняем массивы инлайнов через наш parse_textline
			term_pair_node.term_inlines = parse_textline(term_raw)
			term_pair_node.definition_inlines = parse_textline(definition_raw)

			# 3. Укладываем готовую семантическую пару в стек документа
			stack[-1].nodes.append(term_pair_node)
			return line_num + 1
	
	# --- Шаг Б: Проверка на контекстную пару
	next_idx = line_num + 1
	if next_idx < len(lines):
		p_clean, _, comment_obj= prepare_line(clean_line)
		# Анализируем очищенную строку
		if p_clean.endswith(":"):
			predicate_paragraph = Paragraph()		

			# Сохраняем предикат.
			predicate_paragraph.inlines = parse_textline(p_clean)
			
			# Комментарий добавляем туда же.-- ПАРСЕ ТЕКСТЛИНЕ ДОБАВИЛ
			if comment_obj:
				predicate_paragraph.inlines.append(comment_obj)

			# Анализируем следующую строку. Ищем зависимый элемент.
			type_next, marker_next = parser.detect_node_type(lines[next_idx])

			dependent_node_obj = None
			after_pair_idx = next_idx

			# Развилка А: Зависимым элементом является Список
			if type_next == "LIST_ITEM":
				dependent_node_obj, after_pair_idx = extract_list_block(lines, next_idx, marker_next)


			# Развилка Б: Зависимым элементом является Блочное включение [X ... X]
			elif type_next == "INCL_START":
				from markvan.models import Section
				dummy_root = Section(level=99)
				local_stack = [dummy_root]
				
				# Диспетчер включений отработает и положит готовую ноду внутрь dummy_root
				after_pair_idx = parser_incl.parse_inclusion(lines, next_idx, local_stack, marker_next)
				
				# Проверяем, появилось ли что-то внутри фейкового корня
				if dummy_root.nodes:
					dependent_node_obj = dummy_root.nodes[0]  # Достаем чистое блочное включение!

			elif type_next == "TEXT_LINE":
				dep_paragraph = Paragraph()
				dep_paragraph.inlines = parse_textline(lines[next_idx])
				dependent_node_obj = dep_paragraph
				after_pair_idx = next_idx + 1

			if dependent_node_obj is not None:
				context_pair_node = ContextPair(predicate_node=predicate_paragraph, dependent_node=dependent_node_obj)
				stack[-1].nodes.append(context_pair_node)

				# # Если у предиката был комментарий — бережно укладываем объект в дерево книги
				# if p_comment_obj:
				# 	stack[-1].nodes.append(p_comment_obj)
				return after_pair_idx

	# --- ШАГ Д: ОБЫЧНАЯ ТЕКСТОВАЯ ПРОЗА ---
	p_node = Paragraph()
	p_node.inlines = parse_textline(raw_line)

	stack[-1].nodes.append(p_node)
	return line_num + 1




# ===
# Для def parse_heading
# Числовые веса рангов для правильной чистки стека и построения вложенности
HEADING_WEIGHTS = {
	'part': 1,
	'chapter': 2,
	'header': 3, 
	'subheader': 4, 
	'h3': 5, 
	'h4': 6, 
	'h5': 7, 
	'h6': 8,
	#0: -1  # Минимальный вес для базового корня документа
}


def parse_heading(lines: list[str], line_num: int, stack: list, marker_name: str) -> int:
	"""
	Умный парсер заголовков. 
	Сохраняет текстовую семантику для Heading, но вычисляет числовой уровень для Section.
	Чистит от комментариев ВСЕ строки заголовка (до 3-х штук) и складывает их в поток.
	"""
	# Сюда бережно собираем все служебные комментарии, найденные на строках заголовка
	collected_comments = []

	# === ШАГ 1. РАЗБОР ПЕРВОЙ СТРОКИ (ИДЕНТИФИКАТОР И ВОЗМОЖНОЕ КОМПАКТНОЕ НАЗВАНИЕ) ===
	first_line_text, _, first_comment = prepare_line(lines[line_num])
	if first_comment:
		collected_comments.append(first_comment)
	
	first_line_tstrip = first_line_text.strip()
	
	manual_id = None
	inline_title = ""

	if '#' in first_line_tstrip:
		parts = first_line_tstrip.split('#', 1)
		id_part = parts[1].strip() # Забираем строго то, что ПОСЛЕ решетки (Ваш индекс 1)
		
		# Если после ID идет пробел, значит это компактный заголовок (например: "р146 Парабола")
		if ' ' in id_part:
			id_sub_parts = id_part.split(' ', 1)
			manual_id = id_sub_parts[0].strip()   # Идентификатор: "р146"
			inline_title = id_sub_parts[1].strip() # Название на этой же строке: "Парабола"
		else:
			manual_id = id_part
	else:
		inline_title = first_line_tstrip[3:].strip()

	# === ШАГ 2. СКАНИРОВАНИЕ НАЗВАНИЯ (ПРАВИЛО ДО ДВУХ СТРОК) ===
	header_text_lines = []
	scan_idx = line_num + 1
	total_lines = len(lines)
	
	# Если на первой строке название уже было (компактный вид), мы НЕ сканируем строки ниже!
	if inline_title:
		header_text_lines.append(inline_title)
	else:
		# Классическая схема: проверяем и очищаем до двух строк контента ниже
		for _ in range(2):
			if scan_idx < total_lines and lines[scan_idx].strip():
				# Прогоняем следующую строку через подготовитель
				clean_sub_line, _, sub_comment = prepare_line(lines[scan_idx])
				
				if sub_comment:
					collected_comments.append(sub_comment)
				
				header_text_lines.append(clean_sub_line.strip())
				scan_idx += 1
			else:
				break

	# Семантическое распределение строк по полям (Ваш оригинальный код)
	final_supra = ""
	final_text = ""
	
	if len(header_text_lines) == 2:
		# Если строки две: первая — это Часть 1, вторая — Самое важное!
		final_supra = header_text_lines[0]
		final_text = header_text_lines[1]
	elif len(header_text_lines) == 1:
		# Если строка одна — это просто название
		final_text = header_text_lines[0]

	# Создаем канонический объект заголовка (Ваш класс Heading)
	h_node = Heading(kind=marker_name, text=final_text, id_=manual_id, supra=final_supra)

	# === ШАГ 3. УБОРКА СТЕКА по весам маркеров (Ваш неизменный код) ===
	current_weight = HEADING_WEIGHTS.get(marker_name, 99)

	while len(stack) > 1:
		top_section_marker = getattr(stack[-1], 'marker_kind', 'part')
		if HEADING_WEIGHTS.get(top_section_marker, 0) >= current_weight:
			stack.pop()
		else:
			break

	# Вычисляем реальный числовой уровень вложенности секции-контейнера
	real_numeric_level = len(stack)

	# Создаем новую подсекцию с числовым уровнем
	new_section = Section(level=real_numeric_level)
	new_section.parent = stack[-1]
	new_section.marker_kind = marker_name
	
	# Укладываем заголовок первым элементом контента подсекции
	new_section.nodes.append(h_node)
	
	# === ВОЗВРАЩАЕМ ВЫВОД КОММЕНТАРИЕВ В ПОТОК ===
	# Скидываем всю пачку собранных служебных комментов независимыми узлами строго за заголовком
	for comment_obj in collected_comments:
		p_node = Paragraph()
		p_node.inlines.append(comment_obj) 
		new_section.nodes.append(p_node)
	
	# Саму подсекцию регистрируем в общем хронологическом потоке родителя
	stack[-1].nodes.append(new_section)
	
	# Шагаем внутрь стека
	stack.append(new_section)

	
	return scan_idx


def parse_gspacer(lines: list[str], line_num: int, stack: list, marker) -> int:
	stack[-1].nodes.append(GroupSpacer(marker))
	return line_num + 1

def parse_pause(lines: list[str], line_num: int, stack: list) -> int:
	"""Обрабатывает заголовок-паузу ~~~, добавляя её в текущий раздел."""
	clean_line = lines[line_num].strip()
	# Выкусываем текст, идущий после маркера ~~~
	pause_text = clean_line[3:].strip()
	
	stack[-1].nodes.append(PauseHead(text=pause_text))
	return line_num + 1


def parse_separator(lines: list[str], line_num: int, stack: list) -> int:
	"""
	Обрабатывает линейный разделитель ___.
	Канонически закрывает текущую подсекцию, просто выталкивая её из стека.
	"""
	# 1. Честно фиксируем маркер окончания контента внутри той секции, которую закрываем
	stack[-1].nodes.append(EndSection())
	
	# 2. ПРЯМОЙ ПУТЬ: если мы находимся внутри какой-то подсекции (длина стека больше 1),
	# мы просто делаем pop() и возвращаемся к родительскому контейнеру уровня выше!
	if len(stack) > 1:
		stack.pop()
		
	# Сдвигаем главный цикл на 1 строку вперед
	return line_num + 1



def parse_list(lines: list[str], line_num: int, stack: list, marker: str) -> int:
	"""
	Диспетчер для главного цикла (когда список идёт сам по себе, без двоеточия).
	"""
	# Получаем созданный объект и индекс
	list_block, next_line_idx = extract_list_block(lines, line_num, marker)
	
	# Раз двоеточия не было, просто кладём список как самостоятельную ноду в секцию
	stack[-1].nodes.append(list_block)
	
	return next_line_idx



def extract_list_block(lines: list[str], line_num: int, raw_marker: str) -> tuple[ListBlock, int]:
	"""
	Сборщик пунктов списка.
	На вход сначала первый LIST_ITEM из блока.
	Затем мы перебираем последующие строки в которых может быть:
	- соседний LIST_ITEM 
	- вложенный блок (Табуляция + LIST_ITEM) 
	- TEXT_LINE зависимый абзац(но только один) 
	- ATTACMENT 
	- Пустая строка -- конец блока.
	"""
	clean_marker = raw_marker.lstrip('-')
	# Опеределяем тип маркера ListBlock по первому элементу.
	
	if clean_marker == '':
			kind = "marked"
	elif clean_marker == '#':			
			kind = "auto_numbered"
	else:
			kind = "manual_numbered"

	list_block_obj = ListBlock(kind=kind)
	# Фиксируем эталонный уровень табов ListBlock по первому элементу.
	base_tab_level = len(lines[line_num]) - len(lines[line_num].lstrip('\t'))

	scan_idx = line_num
	total_lines = len(lines)	
	# Переменная для слежки за самым последним созданным пунктом списка.
	last_item_obj = None

	# ^^^ 
	# Перебор всех строк ListBlock (начиная с текущего!(повторно определим его тип))
	while scan_idx < total_lines:
		current_line = lines[scan_idx]
		clean_line = current_line.strip()
		
		# === ПРАВИЛО 1: Пустая строка — конец текущего блока списка.
		if not clean_line:
			break
				
		# === ПРАВИЛО 2: Если табы уменьшились — мы вышли из вложенности, текущий список окончен
		current_tab_level = len(current_line) - len(current_line.lstrip('\t'))
		if current_tab_level < base_tab_level:
			break
		
		# 
		type_check, marker_check = parser.detect_node_type(current_line)
		
		# === СЦЕНАРИЙ А: Пункт списка
		if type_check == "LIST_ITEM":
			# Развилка А1: Соседний пункт на текущем уровне табов (или наш первый)
			if current_tab_level == base_tab_level:	
				manual_number = marker_check[1:] if marker_check.startswith('-') else None
				
				list_item_obj = ListItem(level=current_tab_level, manual_number=manual_number)

				raw_item_text = clean_line[len(marker_check):].strip()
				list_item_obj.inlines = parser_lines.parse_textline(raw_item_text)	

				# Добавляем ListItem в ListBlock	
				list_block_obj.items.append(list_item_obj)

				last_item_obj = list_item_obj

				scan_idx += 1
				continue

			# Развилка А2: Большая вложенность (уходим в рекурсию).
			elif current_tab_level > base_tab_level and last_item_obj is not None:
				# Вызываем сами себя для сбора sub_list_block.
				sub_list_block, next_idx = extract_list_block(lines, scan_idx, marker_check)
				
				# Кладем весь вложенный список в мешок поднод родительского пункта
				last_item_obj.sub_items.append(sub_list_block)
				
				# Перепрыгиваем счётчиком сразу за конец вложенного списка!
				scan_idx = next_idx
				continue

			# Страховочный выход для кривой разметки (защита от бесконечного цикла)
			else:
				scan_idx += 1
				continue

		# === СЦЕНАРИЙ Б: DEPENDENT TEXT_LINE 
		# Если табов больше и у нас есть хозяин
		if type_check == "TEXT_LINE" and current_tab_level > base_tab_level and last_item_obj is not None:
			# Проверяем, нет ли уже зависимого абзаца (по правилу — только один)
			has_paragraph = any(isinstance(n, Paragraph) for n in getattr(last_item_obj, 'sub_items', []))
			
			if not has_paragraph:
				dependet_p = Paragraph()
				dependet_p.inlines = parser_lines.parse_textline(clean_line)
				
				last_item_obj.sub_items.append(dependet_p)
				scan_idx += 1
				continue
			else:
				# Если один абзац уже есть, а табы продолжаются — возможно, это ошибка или чужой блок
				break

		# === СЦЕНАРИЙ В: ATTACHMENT (Служебная ссылка или сноска для текущего пункта списка)
		# === СЦЕНАРИЙ В ВНУТРИ extract_list_block: Поймали служебную строку ссылки/сноски ===
		if type_check == "ATTACHMENT" and last_item_obj is not None:
			# 1. Вызываем создателя объектов напрямую
			new_attach = create_attachment_object(marker_check, clean_line)
			
			if new_attach is not None:
				# 2. Бережно кладём строго в ЛИЧНЫЙ мешок текущего активного пункта списка!
				if not hasattr(last_item_obj, 'attachments') or last_item_obj.attachments is None:
					last_item_obj.attachments = []
				last_item_obj.attachments.append(new_attach)
				
			# 3. СДВИГАЕМ СЧЁТЧИК СТРОК И ПРОДОЛЖАЕМ ЦИКЛ СПИСКА!
			# Никаких выходов, никаких созданийParagraph здесь быть не должно!
			scan_idx += 1
			continue



		# Если строка не подошла ни под один сценарий — список окончательно прерывается
		break

	return list_block_obj, scan_idx





# ===
# Вспомогательные функции


	



def parse_attachment(lines: list[str], line_num: int, stack: list, marker: str) -> int:
	"""
	Главный диспетчер строки вложения верхнего уровня.
	Берёт последнюю физически добавленную ноду из стека текущей секции.
	"""
	current_line = lines[line_num]
	clean_line = current_line.strip()
	# 1. Вызываем нашего создателя объектов (он возвращает Link или FootnoteAttach)
	new_attach = create_attachment_object(marker, clean_line)

	if new_attach is not None:
		# Находим хозяина вложения: смотрим на самую последнюю ноду в активной секции стека!
		if stack and stack[-1].nodes:
			last_node = stack[-1].nodes[-1]
			# Проверяем, есть ли у этой ноды карман для вложений. 
			# Если нет (например, это базовый Node), создаём динамически или пишем в существующий
			if not hasattr(last_node, 'attachments'):
				last_node.attachments = []
				
			last_node.attachments.append(new_attach)
		else:
			# Вызываем твой красивый варнинг по сигнатуре логгера pt
			pt.wrn(
				"Обнаружено вложение без родительского текстового блока.",
				f"\tСтрока автора: {clean_line}",
				True
			)

	return line_num + 1




def create_attachment_object(marker: str, clean_line: str) -> object | None:
	"""
	Универсальный создатель объектов-вложений (Лексер).
	Принимает маркер и очищенную строку, возвращает готовый объект Link или FootnoteAttach.
	"""
	# === РАЗВИЛКА А: Это сноска
	if marker.startswith('|*'):
		full_marker_str = clean_line.split()[0]
		# Первые символы |* отбрасываем для упрощения проверки
		truncated_id = full_marker_str[2:].strip()

		if truncated_id == '#':
			# Сценарий 1: Звезда + решётка ([*#]). 
			id_type = 'auto'
			res_ftn_id = None
		elif truncated_id.isdigit():
			# Сценарий 2: Звезда + Число ([*1], [*2]). 
			id_type = 'manual'
			res_ftn_id = truncated_id
		else:
			# Сценарий 3: Там сидят только звезды ([*], [**], [***])!
			id_type = 'symbol'
# 			# Восполняем потерю
			res_ftn_id = "*" + truncated_id
			
		text_content = clean_line[len(full_marker_str):].strip()

		footnote_obj = FootnoteAttach(id_type=id_type, text=text_content)		
		# А вычисленный текстовый маркер (res_ftn_id) — присваиваем свойством ниже!
		# Для авторежима там будет None, для символов — "*", для мануальных — цифра автора.
		footnote_obj.res_ftn_id = res_ftn_id
		
		return footnote_obj
	
	# === РАЗВИЛКА Б: Это ссылка
	else:

		return parser_lines.parse_link(clean_line)


