"""
Токенизатор содержимого содержимого кодового включения

"""

import re
from html import escape as escape_html
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from utils import ptlog as pt
from exporters.html import uno_hgl

# Список языков для валидации highlighter.py
PYGMENTS_LANGS = [
	# 1. Веб-разработка и стили
	"html", "css", "scss", "sass", "less", "js", "javascript", "ts", "typescript", "jsx", "tsx",
	# 2. Основные языки программирования
	"python", "py", "python3", "go", "golang", "rust", "rs", "c", "cpp", "c++", "csharp", "c#", 
	"java", "kotlin", "kt", "swift", "php", "ruby", "rb", "perl", "pl", "r", "lua",		
	# 3. Базы данных и запросы
	"sql", "mysql", "postgresql", "postgres", "plsql", "nosql", "redis",		
	# 4. Форматы данных и разметка
	"json", "yaml", "yml", "xml", "toml", "ini", "csv", 	
	# 5. Системное администрирование, скрипты и DevOps
	"bash", "sh", "shell", "zsh", "poweshell", "ps1", "dockerfile", "docker", "nginx", "apache", "makefile", "make",		
	# 6. Текстовые расширения
	"markdown", "md", "txt", "plain"
]
# ===
# Диспетчер

def highlight_code(code_list, language: str,) -> str:
	"""
	ГЛАВНЫЙ ДИСПЕТЧЕР ПОДСВЕТКИ.
	Получет словарь строк и возвращает html-текст с выделенными элементами разметки кода.
	"""
	# Сразу собираем монолитную строку для Pygments и фолбеков, очищая хвосты
	code_mono_str = "\n".join(str(line).rstrip('\r\n') for line in code_list)

	if language == 'text':
		return highlight_markvan(code_list)
		
	elif language in ['uno', 'unom', 'unos']:
		#return highlight_uno(code_list)		
		return uno_hgl.convert_code_to_html(code_list)
	
	elif language in PYGMENTS_LANGS:
		try:
			# Передаем строку в твою функцию-обертку Pygments
			pygments_res = highlight_via_pygments(code_mono_str, language)
			
			# === НАШЕ ХИРУРГИЧЕСКОЕ ИСПРАВЛЕНИЕ ДЛЯ PYGMENTS ===
			# Pygments ВСЕГДА дописывает \n в конец HTML. Откусываем ровно ОДИН финальный перенос строки,
			# чтобы закрывающий тег </code> в шаблоне inclusions.py сел идеально впритык!
			if pygments_res.endswith('\n'):
				return pygments_res[:-1]
			return pygments_res
			
		except ClassNotFound:
			# БРOНИРOВAННЫЙ ФOЛБEК-ЩИТ: Если язык неизвестен или автор опечатался
			# Мы точечно экранируем ВЕСЬ код, защищая DOM-дерево от краша, 
			# и возвращаем чистый поток без концевого \n через "\n".join()!
			escaped_lines = [
				f'<span class="text default">{escape_html(str(line).rstrip("\r\n"))}</span>' 
				for line in code_list
			]
			return "\n".join(escaped_lines)
		
	elif language == 'mermaid':
		if isinstance(code_list, list):
			pure_text = "\n".join([str(line) for line in code_list])
		else:
			pure_text = str(code_list)
		return pure_text
	
	else:
		# Незнакомые языки, опечатки
		return escape_html(code_mono_str)
		


# Твой канонический перечень всех парных включений Ядра Маркван
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
	'{$': '$}',  # Инъекция
	'{§': '§}',  # Динамические блоки агрегации (TOC, сноски)
}

# Матрица разрешений: в каких блоках разрешено подсвечивать внутренние инлайны Марквана
INLINE_ALLOWED_BLOCKS = {
	'[(': True,   # В матрешках текста — МОЖНО
	'[[': True,   # В медиа — МОЖНО
	'[|': True,   # В таблицах — МОЖНО
	'[_': True,   # В спойлерах — МОЖНО
	'[.': True,   # В группировках — МОЖНО
	# Для остальных ([&, [%, [`, [/]) по умолчанию будет False (строгий raw-текст)
}



# =====================================================================
# 2. КАСТОМНЫЙ ТОКЕНИЗАТОР ДЛЯ CONFIG-ФАЙЛОВ UNO (uno, unom, unos)
# =====================================================================
def highlight_uno(code_text: str) -> str:
	"""
	Официальный токенизатор синтаксиса UNO.
	Генерирует чистые HTML-классы для конфигурационных файлов.
	"""
	if isinstance(code_text, list):
		pt.deb(code_text)

	escaped = escape_html(code_text)
	
	uno_rules = [
		(r'(^\s*(?:#|//).*$)', 'uno-comment'),
		(r'(^[a-zA-Z0-9_\-]+)(?=\s*[:=])', 'uno-key'),
		(r'([:=])', 'uno-operator'),
		(r'\b(true|false|yes|no|on|off)\b', 'uno-constant'),
		(r'\b\d Graham\b|\b\d+(\.\d+)?\b', 'uno-number'),
	]
	
	for pattern, css_class in uno_rules:
		escaped = re.sub(pattern, f'<span class="{css_class}">\\1</span>', escaped, flags=re.MULTILINE)
		
	return escaped





def highlight_via_pygments(code_text: str, language: str) -> str:
	"""
	Отрабатывает стандартные мировые языки программирования.
	Выдает чистую подсветку ключевых слов. Упаковку в строки контролирует наш генератор.
	"""
	lexer = get_lexer_by_name(language.strip().lower(), stripall=True)

	# ШАГ 1: Говорим Pygments выдать ТОЛЬКО чистые спаны цветов, без оберток и номеров
	formatter = HtmlFormatter(nowrap=True, noclasses=False)

	try:
		# Получаем сплошной HTML со спанами подсветки, где строки разделены обычным \n
		raw_html = highlight(code_text, lexer, formatter)
		
		# ШАГ 2: Честно режем полученный HTML на строки в Python
		lines = raw_html.split('\n')
		if lines and not lines[-1]: # Pygments всегда кидает пустую строку в конец, убираем её
			lines.pop()

		html_lines = []
		# ШАГ 3: Сами, вручную, собираем идеальную иерархию для каждой строки!
		for i, line_content in enumerate(lines, start=1):
			# Упаковываем табы в спаны на передовой
			clean_line = line_content.replace('\t', '<span class="tab">\t</span>')
#			clean_line = re.sub(r' (?=[^>]*<(?:/?[a-zA-Z0-9]+)?(?:>|\s))', '&nbsp;', clean_line)
			# Собираем строчку: жестко контролируем, чтобы внутри тега <span> НЕ было никаких переносов!
			formatted_line = (
				# f'<span id="line-{i}">'
				# f'<span class="linenos">{i}</span>'
				# f'{clean_line}'
				# f'</span>'
				f'<span id="line-{i}">'
				f'<span class="linenos">{i}</span>'
				f'<code class="code-content">{clean_line}</code>'
				f'</span>'
			)
			html_lines.append(formatted_line)

		# Склеиваем строки через \n, который находится СНАРУЖИ тегов <span> и никогда не создаст пустых этажей!
		return "\n".join(html_lines)

	except Exception:
		return escape_html(code_text)


def highlight_inline_code(code_text: str, language: str) -> str:
	"""
	УЛЬТИМАТИВНЫЙ СТРОЧНЫЙ ХАЙЛАЙТЕР (Для InlineIncl).
	Жестко гарантирует отсутствие номеров строк, анкоров и переносов!
	Выдает только чистые разноцветные span-теги синтаксиса.
	"""
	if not code_text.strip():
		return ""
		
	try:
		# Достаем нужный лексер (например, для rust)
		lexer = get_lexer_by_name(language, stripall=True)
	except Exception:
		# Если язык не передан или не распознан — отдаем безопасный текст без краша
		return escape_html(code_text)
		
	# === ГЛАВНЫЙ СЕКРЕТ ШЕРИФА: nowrap=True ===
	# Этот параметр полностью сносит к чертям генерацию номеров строк,
	# убирает блоки pre/div и запрещает нарезать текст на линии!
	formatter = HtmlFormatter(nowrap=True)
	
	# Склеиваем массив строк в плоский текст, если прилетел список, 
	# но для инлайна там обычно одна чистая строка.
	if isinstance(code_text, list):
		pure_text = "".join(str(line) for line in code_text)
	else:
		pure_text = str(code_text)
		
	# Запускаем подсветку и жестко отсекаем концевые невидимые пробелы/переносы
	return highlight(pure_text, lexer, formatter).strip()

#===
# ===
# Markvan

# Твоя каноническая карта парных включений
INCLUSION_PAIRS = {
	'[(': ')]',  # Блоки-матрешки текста
	'[/': '/]',  # Комментарии 
	'[`': '`]',  # Преформатированный текст
	'[&': '&]',  # Код
	'[%': '%]',  # Формулы
	'[[': ']]',  # Медиа
	'[|': '|]',  # Таблицы
	'[.': '.]',  # Группировки
	'[_': '_]',  # Спойлеры
	'[$': '$]',  # Блок интерактивного ввода данных
	'{&': '&}',  # Инъекция
	'{§': '§}',  # Динамические блоки агрегации (TOC)
}

# Матрица разрешений инлайновой подсветки
INLINE_ALLOWED_BLOCKS = {
	'[(': True,
	'[[': True,
	'[|': True,
	'[_': True,
	'[.': True,
}













def highlight_markvan(code_text: list) -> str:
	"""
	ТОКЕНИЗАТОР MARKVAN.
	Посимвольно сканирует скобки блоков, а инлайны накатывает перед выдачей.
	Ультимативно очищен от скрытых переносов \n и спанов-призраков!
	"""
	html_lines = []
	bracket_stack = []
	
	header_state = None
	in_table_zone = False

	for line in code_text:
		
		# === 1. Если пустая строка
		if not line.strip():
			html_lines.append('<span class="text empty-line"></span>')
			continue

		# === 2. Выделяем ссылку и комментарий
		# Вычисляем класс строки на основе текущего состояния стека скобок
		lvl = min(len(bracket_stack), 4)
		current_line_class = f"text incl-l{lvl}" if lvl > 0 else "text"

		clean_line, link_html, comment_html = prepare_line_assets(line, current_line_class)
	
		# === 3. Вычисляем контекст местонахождения: можем ли подсвечивать код.
		current_top_block = bracket_stack[-1] if bracket_stack else None
		is_inline_allowed = True
		
		if current_top_block is not None and not INLINE_ALLOWED_BLOCKS.get(current_top_block, False):
			is_inline_allowed = False

		# === 4. Обработка маркеров включений
		idx = 0
		processed_line = ""
		
		while idx < len(clean_line):
			token_2 = clean_line[idx:idx+2]

			# А: Открывающий маркер включения
			if token_2 in INCLUSION_PAIRS:
				lvl = min(len(bracket_stack), 3)
				bracket_stack.append(token_2)
				
				if token_2 == "[|":
					in_table_zone = True
				
				type_match = re.match(r'^([\w\d_\-!]+)', clean_line[idx+2:])
				block_type = type_match.group(1) if type_match else ""
				idx_offset = len(block_type)
				
				id_match = re.match(r'^\s*(#[\w\d_\-]+)', clean_line[idx+2+idx_offset:])
				block_id = id_match.group(1) if id_match else ""
				
				processed_line += f'<span class="marker bracket-l{lvl}">{escape_html(token_2)}</span>'
				
				if block_type:
					processed_line += f'<span class="block-type">{escape_html(block_type)}</span>'
					idx += idx_offset
					
				if block_id:
					full_id_match = re.match(r'^(\s*#[\w\d_\-]+)', clean_line[idx+2:])
					full_id_str = full_id_match.group(1) if full_id_match else block_id
					
					processed_line += f'<span class="block-id">{escape_html(full_id_str)}</span>'
					idx += len(full_id_str)
				
				idx += 2
				continue

			# Б: Закрывающий маркер
			if bracket_stack:
				found_match_idx = -1
				for s_idx in range(len(bracket_stack) - 1, -1, -1):
					if token_2 == INCLUSION_PAIRS[bracket_stack[s_idx]]:
						found_match_idx = s_idx
						break
				if found_match_idx != -1:
					if bracket_stack[found_match_idx] == "[|": 
						in_table_zone = False
					lvl = min(found_match_idx, 3)
					bracket_stack = bracket_stack[:found_match_idx]
					processed_line += f'<span class="marker bracket-l{lvl}">{escape_html(token_2)}</span>'
					idx += 2
					continue
					
			# В: Обычные символы текста — экранируем БЕЗОПАСНО, сохраняя пробелы в чистом виде!
			# ЖEЛEЗНO ИСПРAВИЛИ: Читаем символы строго из очищенной clean_line!
			processed_line += escape_html(clean_line[idx])
			idx += 1

		# === 5: Обработка заголовков
		if not in_table_zone:
			found_marker = None
			is_bold = False		
			
			# Для сравнения маркеров сами временно зачищаем строку СЛЕВА через .lstrip()
			left_clean_strip = clean_line.lstrip()
			
			for m in ['***', '^^^', '"""', '===', '---', '...']: 
				if left_clean_strip.startswith(m): 
					found_marker = m
					is_bold = True
					break
			if not found_marker:
				for m in [',,,', ':::', ';;;', '~~~']:
					if left_clean_strip.startswith(m): 
						found_marker = m
						is_bold = False
						break
						
			if found_marker:
				# Находим точный индекс, где сидит маркер в строке clean_line
				marker_pos = clean_line.find(found_marker)
				
				# rest_text — это всё, что идёт ПОСЛЕ маркера (сохраняем пробелы перед решёткой!)
				rest_text = clean_line[marker_pos + len(found_marker):]
				
				block_id = ""
				inline_title = ""
				
				# Проверяем наличие решётки: стрипим rest_text только СЛЕВА
				if rest_text.lstrip().startswith('#'):
					# Находим точный индекс решётки
					hash_pos = rest_text.find('#')
					
					# МAГИЧEСКOE ИСПРAВЛEНИE: Забираем пробелы, которые автор поставил МЕЖДУ маркером и ID!
					spaces_before_id = rest_text[:hash_pos]
					
					id_part = rest_text[hash_pos:] # Сам ID (от решётки и дальше)
					
					# Делим строго по первому пробелу после ID
					parts = id_part.split(' ', 1)
					block_id = parts[0].strip() # Сам ID зачищаем полностью
					
					if len(parts) == 2:
						# Забираем название, сохраняя его левые пробелы через .rstrip()
						inline_title = parts[1].rstrip('\r\n') 
						
					# Вшиваем выжившие пробелы прямо перед блоком ID!
					block_id_html = f'{spaces_before_id}<span class="block-id">{escape_html(block_id)}</span>'
				else:
					# Решётки нет — весь хвост после маркера становится названием
					inline_title = rest_text.rstrip('\r\n')
					block_id_html = ""

				
				# Взводим состояние для следующей строки, если названия тут нет
				header_state = None if inline_title else ("bold" if is_bold else "normal")
				
				# Сборка processed_line
				spaces_before = clean_line[:marker_pos]
				processed_line = f'{spaces_before}<span class="marker headers">{found_marker}</span>'
				
				# Подставляем ID вместе с сохраненными пробелами перед ним!
				if block_id_html:
					processed_line += block_id_html
				
				if inline_title:
					sub_class = "text header-bold" if is_bold else "text header-normal"
					processed_line += f'<span class="{sub_class}">{escape_html(inline_title)}</span>'

		# === 6. СИНТАКСИС ТАБЛИЦ Марквана
		if in_table_zone:
			if clean_line in ['---', '===']:
				processed_line = processed_line.replace(clean_line, f'<span class="marker table-separator">{clean_line}</span>')
			else:
				processed_line = re.sub(
					r'(\|#|\|=|\|&lt;|\||!|\.|\:)', 
					r'<span class="marker table-cell">\1</span>', 
					processed_line
				)

		# === 7. Обрабатываем строчные элементы
		if is_inline_allowed:
			processed_line = render_inline_nodes(processed_line)

		# === 8: Склейка полученных html- элементов
		if header_state == "bold":
			x_class = "text header-bold"
			header_state = None
			
		elif header_state == "normal":
			x_class = "text header-normal"
			header_state = None
			
		elif in_table_zone:
			x_class = "text table-row"
		else:
			lvl = min(len(bracket_stack), 3)
			x_class = f"text incl-l{lvl}" if lvl > 0 else "text default"

		# Если у нас в процессе конвейера выжила ссылка от текста — вшиваем её в конец полезного контента
		if link_html:
			processed_line += f"{link_html}"
			if comment_html:
				processed_line += f" {comment_html}"
			
		# Если ссылки не было, но был обычный текстовый комментарий в конце строки
		elif comment_html:
			processed_line += f"{comment_html}"

		processed_line = processed_line.replace('\t', '<span class="tab">\t</span>')

		# Запечатываем всё в единый монолитный спан-строку
		html_lines.append(f'<span class="{x_class}">{processed_line}</span>')

	return "\n".join(html_lines)


# ---


COMMENT_REGEX = re.compile(r'(``.*?``)|(///|//\?|//!)')
# Паттерн теперь ищет: или "|>>", или "|>", или "|->" с обязательным пробелом после них
#LINE_REDIRECT_REGEX = re.compile(r'\s*(\|>>?|\|->)\s+(.*)$')
#LINE_REDIRECT_REGEX = re.compile(r'\s*(\|>>?|\|->)\s+([^/]+)(.*)$')
LINE_REDIRECT_REGEX = re.compile(r'\s*(\|>>?|\|->)\s+(.*)$')

def prepare_line_assets(striped_line: str, line_class: str) -> tuple[str, str | None, str | None]:
	"""
	ПОДГОТОВИТЕЛЬ ИНЛАЙН-РЕСУРСОВ СТРОКИ.
	Изолирует комментарий и ссылку, сохраняя правильный класс вложенности.
	Возвращает: (очищенная_строка, html_ссылки, html_комментария)
	"""
	link_html = None
	comment_html = None
	clean_line_notcom = striped_line #если не найдём комментарий
	
	# === ЭТАП 1. ПОДГОТОВКА КОММЕНТАРИЯ (Строгий распил на маркер и текст)
	has_comment = False
	for match in COMMENT_REGEX.finditer(striped_line):
		if match.group(1): 
			continue  # Пропускаем экранированные ``///``
			
		if match.group(2):
			has_comment = True
			marker_start = match.start(2)
			marker = match.group(2)
			
			# Намертво отсекаем комментарий из строки для всех последующих шагов!
			clean_line_notcom = striped_line[:marker_start]
			
			# Собираем comment_html...
			comment_text = striped_line[marker_start:]
			c_kind = 'todo' if marker == '//!' else ('issue' if marker == '//?' else 'note')
			c_marker = comment_text[:3]
			c_text = comment_text[3:]
			
			comment_html = (
				f'<span class="marker comment {c_kind}">{escape_html(c_marker)}</span>'
				f'<span class="text comment {c_kind}">{escape_html(c_text)}</span>'
			)
			break  # Выходим, clean_line_notcom успешно зафиксирована!

	# === ЭТАП 2. ПОДГОТОВКА ССЫЛКИ (Работает со строкой, ОЧИЩЕННОЙ от комментария)
	#if '|> ' in clean_line or '|>> 'in clean_line or '|-> 'in clean_line:
	link_match = LINE_REDIRECT_REGEX.search(clean_line_notcom)
	
	if link_match:
		# Вычисляем текст до ссылки, основываясь на текущей clean_line
		text_before_link = clean_line_notcom[:link_match.start()]
		marker = link_match.group(1).strip()
		rest = link_match.group(2).strip()
		
		address = rest
		description = ""
		pipe = ""
		
		if '|' in rest:
			parts = rest.split('|', 1)
			address = parts[0].strip()
			pipe = "|"
			description = parts[1].strip()

		# Собираем внутреннюю начинку ссылки
		html_res = ""
		html_res += f'<span class="marker link-address">{escape_html(marker)}</span> '
		html_res += f'<span class="text link-address">{escape_html(address)}</span>'
		
		if pipe and description:
			html_res += f'<span class="marker link-address">{escape_html(pipe)}</span> '
			html_res += f'<span class="link-text">{escape_html(description)}</span>'
			
		# Оборачиваем ВСЮ готовую ссылку целиком в её законный класс строки
		#link_html = f'<span class="{line_class}">{html_res}</span>'
		link_html = html_res

		# Для посимвольного сканера чистая строка сжимается до текста ДО ссылки
		clean_line_notcom = text_before_link
	# else:
	# 	clean_line_notcom = striped_line

	# Возвращаем строго clean_line, которая прошла через фильтрацию коммента и ссылки!
	return clean_line_notcom, link_html, comment_html



def render_inline_nodes(safe_text: str) -> str:
	"""
	НАКАТЫВАЕМ СТРОГИЕ ИНЛАЙНЫ МАРКВАНА.
	Прогоняет очищенный текст через каскад регулярных выражений синтаксиса.
	"""
	if not safe_text.strip():
		return safe_text

	processed_line = safe_text

	# === СИНТАКСИЧЕСКАЯ ПОДСВЕТКА СТРОЧНОГО СПОЙЛЕРА ШЕРИФА ===
	# Ловит открывающий маркер _[, полезный контент и закрывающий маркер ]_
	# Оборачивает весь блок в интерактивный span, а сами маркеры подсвечивает классом marker styles
	processed_line = re.sub(
		r'(_\[)(.*?)(\]_)',
		r'<span class="spoiler-text"><span class="marker styles">\1</span>\2<span class="marker styles">\3</span></span>',
		processed_line
	)
	processed_line = re.sub(r'(^\s*-(?:[0-9]+\.?|[IVXLCDMivxlcdm]+\.?|[a-zA-Zа-яА-ЯёЁ][\)]?|#)?\s)', r'<span class="marker lists">\1</span>', processed_line)
	processed_line = re.sub(r'(\[)(\*+[0-9]*)(\])', r'<span class="marker footnotes">\1\2\3</span>', processed_line)
	processed_line = re.sub(r'(^\s*\|)(\*+[0-9]*|\*+)(?=\s)', r'<span class="marker footnotes">\1\2</span>', processed_line, flags=re.MULTILINE)
	processed_line = re.sub(r'(\*\*|~~|``|\^\^|__)(.*?)(\1)', r'<span class="marker styles">\1</span>\2<span class="marker styles">\3</span>', processed_line)

	asym_pairs = [
		(r'~_', r'_~'), (r'~\^', r'\^~'), (r'~-', r'-\~'),
		(r'\*-', r'-\*'), (r'-\*', r'\*-'), (r'!-', r'-!'), (r'!\+', r'\+!')
	]
	for start_p, end_p in asym_pairs:
		processed_line = re.sub(f'({start_p})(.*?)({end_p})', r'<span class="marker styles">\1</span>\2<span class="marker styles">\3</span>', processed_line)

	processed_line = re.sub(
		r'(%\[|&amp;\[|\$\[)(.*?)(\]%|\]&amp;|\]\$)([\w\d_\-]+)?',
		r'<span class="marker inline-incl">\1</span><span class="text raw-content">\2</span><span class="marker inline-incl">\3</span><span class="block-type">\4</span>',
		processed_line
	)

	processed_line = re.sub(r'(\{\$[a-zA-Z0-9_\-]+\})', r'<span class="variable">\1</span>', processed_line)
	# Универсальный поиск: ловит <[ абсолютно любое слово или фразу ]>
	processed_line = re.sub(
		r'(&lt;\[)(.*?)(\]&gt;)', 
		r'<span class="marker link-bracket">\1</span><span class="link-text">\2</span><span class="marker link-bracket">\3</span>', 
		processed_line
	)

	return processed_line
