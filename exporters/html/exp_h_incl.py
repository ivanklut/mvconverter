	# ***
	# Блочные включения [X … X]
import os
from html import escape as escape_html

from utils import ptlog as pt
from exporters.html import exp_h_highlighter
from exporters.html import exporter_html

from exporters import doc_exporter


def render_text_incl(node, indent) -> str:
	"""
	Рендеринг текстового включения [( )].
	"""
	gtab = indent + "\t"
	id_attr = f' id="{node.id}"' if hasattr(node, 'id') and node.id else ""
	class_attr = node.incl_class

	figcaption_html = ""
	caption_lines = []

	if node.title:
		caption_lines.append(f"{gtab}\t<incl-title>{escape_html(node.title)}</incl-title>")
	if node.description:
		caption_lines.append(f"{gtab}\t<incl-descr>{escape_html(node.description)}</incl-descr>")
		
	figcaption_html = _render_figcaption(node, gtab)
	
	body_html = exporter_html.render_nodes_flow(node.nodes, gtab + "\t")
	
	raw_html = f"""{indent}<figure class="text {class_attr}"{id_attr}>
{figcaption_html}{gtab}<incl-body>
{body_html}
{gtab}</incl-body>
{indent}</figure>"""

	return raw_html.rstrip("\t")


def render_comment_incl(node, indent) -> str:
	"""
	Рендеринг блочного комментария автора [/ … /].
	"""
	# Импортируем зрячий флаг напрямую из общей памяти билдера!
	from exporters.doc_exporter import HIDE_COMMENTS
	
	# СТРОГОЕ И ЧИСТОЕ УСЛОВИЕ:
	if HIDE_COMMENTS:
		return ""
		
	gtab = indent + "\t"
	id_attr = f' id="{node.id}"' if getattr(node, 'id', '') else ""
	class_attr = node.incl_class

	# Вызов локальной функции без self.!
	figcaption_html = _render_figcaption(node, gtab)

	# ЖEЛEЗНO ИСПРAВИЛИ: Передаем каноничный массив ОБЪЕКТОВ нод (node.nodes вместо raw_lines)
	# чтобы главный диспетчер успешно отрендерил всё внутреннее мясо комментария!
	body_html = exporter_html.render_nodes_flow(node.nodes, gtab + "\t")

	# Безупречный HTML-каркас карточки Маркван
	raw_html = f"""{indent}<figure class="comment {class_attr}"{id_attr}>
{figcaption_html}{gtab}<incl-body>{body_html}</incl-body>
{indent}</figure>"""
	
	return raw_html.rstrip("\t ")





def render_pre_incl(n, indent) -> str:
	"""
	Рендеринг преформатированного текста [` … `].
	Абсолютно чистая системная геометрия без костылей .replace() и rstrip().
	Полностью интегрирован с универсальным сборщиком подписей!
	"""
	from html import escape as escape_html

	gtab = indent + "\t"
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	class_attr = n.incl_class
	
	# === ШАГ 1: СНАЙПЕРСКИЙ ВЫЗОВ НАШЕЙ МИКРОФУНКЦИИ ПОДПИСЕЙ ===
	# Сама соберёт <incl-title>, <incl-descr> и многострочные <incl-comment> !
	figcaption_html = _render_figcaption(n, gtab)
	
	# === ШАГ 2: СБОРКА СТАТИЧЕСКОГО ТЕЛА КОДА ===
	# Извлекаем сырые строки. По канону Группы 2 они лежат девственно чистыми в raw_lines
	lines = getattr(n, 'raw_lines', getattr(n, 'body_lines', []))
	
	# Очищаем строки от системных концевых переносов и склеиваем через \n
	cleaned_lines = [str(line).rstrip('\r\n') for line in lines]
	pure_text = escape_html("\n".join(cleaned_lines))
	
	# === ШАГ 3: ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И КРАСИВЫЙ HTML-ШАБЛОН ===
	# {pure_text} прижат к левому краю, так как внутри тега code сохраняются все авторские табы!
	# Закрывающие кавычки """ стоят на отдельной строке, нативно генерируя финальный \n для Касты Б.
# 	raw_html = f"""{indent}<figure class="pre {class_attr}"{id_attr}>
# {figcaption_html}{gtab}<pre><code class="incl-body">{pure_text}</code></pre>
# {indent}</figure>"""

	raw_html = f"""{indent}<figure class="pre {class_attr}"{id_attr}>
{figcaption_html}{gtab}
<pre class="incl-body">{pure_text}</pre>
{indent}</figure>"""


	# Срезаем случайные правые табы и пробелы (\t ), оставляя нативный \n от кавычек!
	return raw_html.rstrip("\t ")



def render_code_incl(n, indent) -> str:
	"""
	Рендеринг блока кода [& … &].
	Абсолютно чистая системная геометрия без костылей .replace() и плейсхолдеров!
	Полностью синхронизирован с универсальным сборщиком подписей _render_figcaption.
	"""


	# === Шаг 1. Создание подписи к включению
	gtab = indent + "\t"
	# Локальная функция сама соберёт <incl-title>, <incl-descr> и многострочные <incl-comment> !
	figcaption_html = _render_figcaption(n, gtab)
	
	# === Шаг 2: Получение сырых строк и токенизация кода
	code_lines = getattr(n, 'raw_lines', getattr(n, 'body_lines', []))
	
	highlighted_code = exp_h_highlighter.highlight_code(code_lines, n.incl_class)

	# === Шаг 3. Формирование атрибутов для вставки в html


	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""

	# Добавляем класс pygments для языков, которые он подсветил.
	class_attr = n.incl_class
	if class_attr in exp_h_highlighter.PYGMENTS_LANGS:
		class_attr = f'{class_attr} pygments' 

	# === Шаг 4. Готовый html включения

	raw_html = f"""{indent}<figure class="code {class_attr}"{id_attr}>
{figcaption_html}{gtab}<code class="incl-body">{highlighted_code}{gtab}</code>
{indent}</figure>
"""
	return raw_html.rstrip("\t ")


def render_formula_incl(n, indent) -> str:
	"""
	Рендеринг формул [% … %].
	Абсолютно чистая геометрия без костылей .replace() и ручной склейки h4/p!
	"""
	gtab = indent + "\t"
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	class_attr = n.incl_class
	
	# === ШАГ 1: КАНOНИЧEСКИЙ ВЫЗOВ УНИВЕРСАЛЬНЫХ ПОДПИСЕЙ ===
	# Локальная функция сама соберёт <incl-title>, <incl-descr> и многострочные <incl-comment>!
	figcaption_html = _render_figcaption(n, gtab)
	
	# === ШАГ 2: ИЗВЛЕЧЕНИЕ ТЕКСТА ФОРМУЛЫ ===
	tag = 'math' if class_attr == 'mathml' else 'div'
	lines = getattr(n, 'raw_lines', getattr(n, 'body_lines', []))
	
	# Очищаем строки от системных переносов и склеиваем. 
	# По твоей спецификации контент внутри MathML/MathJax НЕ экранируем!
	cleaned_lines = [str(line).rstrip('\r\n') for line in lines]
	raw_content = "\n".join(cleaned_lines)
	
	# === ШАГ 3: ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И ЗAЖAТЫЙ HTML-ШАБЛОН ===
	# Переменная {raw_content} прижата к левому краю, защищая математический синтаксис от лишних табов.
	# Теги закрытия </{tag}> прижаты впритык, полностью исключая появление плашек «пробел»!
	raw_html = f"""{indent}<figure class="math {class_attr}"{id_attr}>
{figcaption_html}{gtab}<{tag} class="incl-body">{raw_content}</{tag}>
{indent}</figure>
"""

	# Срезаем случайные правые табы и пробелы (\t ), оставляя нативный \n от кавычек!
	return raw_html.rstrip("\t ")




# ===
# Группа функций медиавключения

# ---
# ДИСПEТЧEР МEДИAВКЛЮЧEНИЙ


def render_media_incl(node, indent) -> str:
	"""
	Диспетчер рендеринга медиавключений [[ … ]].
	"""
	gtab = indent + "\t"


	# Вычисляем базовый класс из ноды
	media_class = node.incl_class
	media_class = str(media_class).strip().lower()
	
	id_attr = f' id="{node.id}"' if getattr(node, 'id', '') else ''
	default_alt = "" #escape_html(getattr(node, 'title', "Иллюстрация"))
	
	# Собираем описание включения
	figcaption_html = _render_figcaption(node, gtab)
	
	# 
	media_items = getattr(node, 'items', [])
	count_gallery = len(media_items)


	# передаём в обработку
	match media_class:
		case 'image':
			return _render_gallery_images(media_items, figcaption_html, media_class, id_attr, gtab, indent, default_alt, count_gallery)
		case "audio":
			return _render_gallery_audio(media_items, figcaption_html, media_class, id_attr, gtab, indent)
		case "video":
			return _render_gallery_video(media_items, figcaption_html, media_class, id_attr, gtab, indent)
		case 'pictogram':
			return _render_pictogram(media_items, media_class, id_attr, gtab, indent, default_alt)
		case _:
			pt.wrn('Класс медиавключения не определён', media_class)
			return ''	
			


def _prepare_media_item_context(item, default_alt):
	"""
	Служебный калибратор Марквана. 
	Берет медиа-ноду, достает пути, защищает от None и пилит .webp пресеты.
	"""
	src_obj = getattr(item, 'src_path', None)
	if not src_obj:
		# Если это аудио/видео без src_path (сломанный слаг)
		slug_path = getattr(item, 'slug_path', '')
		return {
			"base_path": slug_path, "view": slug_path, "flscreen": slug_path, "thumb": slug_path,
			"alt": default_alt, "action_url": None
		}

	# Извлекаем метаданные
	src_title = getattr(src_obj, 'title', '')
	safe_caption = escape_html(str(src_title))
	safe_alt = safe_caption if safe_caption else default_alt

	# Калибруем базовый путь
	base_path_src = doc_exporter.get_web_path(src_obj)
	safe_src_path = base_path_src if base_path_src is not None else ""
	
	# Пилим расширение
	path_without_ext, _ = os.path.splitext(safe_src_path)

	if getattr(src_obj, 'type', 'local') == 'global':
		path_flscreen = safe_src_path
		path_view     = safe_src_path
		path_thumb    = safe_src_path
	else:
		path_flscreen = f"{path_without_ext}~flscreen.webp"
		path_view     = f"{path_without_ext}~view.webp"
		path_thumb    = f"{path_without_ext}~thumb.webp"

	# Проверяем внешнюю ссылку-действие
	action_url = None
	if getattr(item, "action_link", None) is not None:
		action_url = doc_exporter.get_web_path(item.action_link)

	return {
		"base_path": safe_src_path,
		"view": path_view,
		"flscreen": path_flscreen,
		"thumb": path_thumb,
		"alt": safe_alt,
		"action_url": action_url
	}






def _render_gallery_images(media_items, figcaption_html, media_class, id_attr, gtab, indent, default_alt, count_gallery, exporter_context=None):
	"""Законы рендеринга адаптивных изображений и галерей."""
	item_blocks = []
	has_action_link = False

	for item in media_items:
		ctx = _prepare_media_item_context(item, default_alt)
		
		if ctx["action_url"]:
			has_action_link = True
			item_html = f"""{gtab}\t\t<a href="{ctx['action_url']}" class="media-target-link" target="_blank">
{gtab}\t\t\t<img src="{ctx['view']}" loading="lazy" alt="{ctx['alt']}">
{gtab}\t\t</a>"""
		elif count_gallery > 1:
			item_html = f"""{gtab}\t\t<a href="{ctx['flscreen']}" class="media-zoom" data-source="{ctx['base_path']}">
{gtab}\t\t\t<img src="{ctx['thumb']}" loading="lazy" alt="{ctx['alt']}">
{gtab}\t\t</a>"""
		else:
			item_html = f"""{gtab}\t\t<a href="{ctx['flscreen']}" class="media-zoom" data-source="{ctx['base_path']}">
{gtab}\t\t\t<img src="{ctx['view']}" loading="lazy" alt="{ctx['alt']}">
{gtab}\t\t</a>"""
			
		item_blocks.append(item_html)

	# Вычисляем финальный класс фигуры на основе структуры данных, а не в цикле!
	suffix_class = ' image'
	if has_action_link:
		suffix_class = ' image'
	elif count_gallery > 1:
		suffix_class = f' gallery items-{count_gallery}'

	body_html = "\n".join(item_blocks)
	return f"""{indent}<figure class="media{suffix_class}"{id_attr}>
{gtab}<incl-body>
{body_html}
{gtab}</incl-body>
{figcaption_html}
{indent}</figure>
""".rstrip("\t ")

def _render_pictogram(items, class_str, id_attr, gtab, indent, default_alt, exporter_context=None):
	"""Законы рендеринга легковесных пиктограмм и авторских иконок pic/picto."""
	item_blocks = []
	for item in items:
		ctx = _prepare_media_item_context(item, default_alt)
		item_html = f'{gtab}\t\t<img class="{class_str}" src="{ctx["view"]}" loading="lazy" alt="{ctx["alt"]}">'
		if ctx["action_url"]:
			item_html = f"""{gtab}\t\t<a href="{ctx['action_url']}" class="media-target-link" target="_blank">\n{gtab}\t{item_html}\n{gtab}\t\t</a>"""
		item_blocks.append(item_html)
		
	body_html = "\n".join(item_blocks)
	return f"""{indent}{gtab}{body_html}""".rstrip("\t ")


def _render_gallery_audio(items, figcaption_html, class_str, id_attr, gtab, indent, exporter_context=None):
	"""Законы рендеринга аудиоплееров."""
	item_blocks = []
	for item in items:
		ctx = _prepare_media_item_context(item, "Аудиозапись")
		item_blocks.append(f'{gtab}\t\t<audio controls src="{ctx["base_path"]}"></audio>')
		
	body_html = "\n".join(item_blocks)
	return f"""{indent}<figure class="media{class_str}"{id_attr}>
{figcaption_html}{gtab}<incl-body>
{body_html}
{gtab}</incl-body>
{indent}</figure>
""".rstrip("\t ")


def _render_gallery_video(items, figcaption_html, class_str, id_attr, gtab, indent, exporter_context=None):
	"""Законы рендеринга видеоплееров."""
	item_blocks = []
	for item in items:
		ctx = _prepare_media_item_context(item, "Видеозапись")
		item_blocks.append(f'{gtab}\t\t<video controls src="{ctx["base_path"]}"></video>')
		
	body_html = "\n".join(item_blocks)
	return f"""{indent}<figure class="media {class_str}"{id_attr}>
{figcaption_html}{gtab}<incl-body>
{body_html}
{gtab}</incl-body>
{indent}</figure>
""".rstrip("\t ")



# ___ Конец медиавключения


def render_table_incl(n, indent) -> str:
	"""
	Рендеринг таблиц [| … |].
	Автоматически сопоставляет сложную геометрию шапки и прописывает адаптивный data-label ячейкам тела!
	Избавлена от костылей .replace() и интегрирована со сборщиком подписей.
	"""
	gtab = indent + "\t"
	incl_class = n.incl_class

	node_id = getattr(n, 'id', '')
	
	class_attr = f' class="{incl_class}"' if incl_class else ""
	id_attr = f' id="{node_id}"' if node_id else ""
	
	# === ШАГ 1: КАНOНИЧEСКИЙ ВЫЗOВ УНИВЕРСАЛЬНЫХ ПОДПИСЕЙ ===
	figcaption_html = _render_figcaption(n, gtab)

	# Извлекаем семантические зоны из AST-ноды Марквана
	thead_rows = getattr(n, 'thead_rows', [])
	tbody_rows = getattr(n, 'tbody_rows', [])
	tfoot_rows = getattr(n, 'tfoot_rows', [])

	# === ШАГ 2: СБОРКА И АНАЛИЗ ТЕКСТОВОЙ КАРТЫ ШАПКИ ===
	# Создаем массив, где индекс — это физический номер колонки, а значение — текст заголовка
	header_labels = {}
	
	# Сначала вытягиваем чистый текст из ячеек первого ряда шапки
	if thead_rows:
		for cell in thead_rows[0].cells:
			c_phys = getattr(cell, '_phys_col', None)
			if c_phys is not None and not getattr(cell, 'is_phantom', False):
				c_span = getattr(cell, 'colspan', 1)
				# Очищаем текст ячейки от разметки для использования в атрибуте
				cell_text = getattr(cell, 'text', '').strip()
				# Прописываем этот заголовок для всех физических колонок, которые он накрывает своим colspan
				for dc in range(c_span):
					header_labels[c_phys + dc] = cell_text

		# Если в шапке есть второй ряд (например, опт/розница под ценой), красиво склеиваем их!
		if len(thead_rows) > 1:
			for cell in thead_rows[1].cells:
				c_phys = getattr(cell, '_phys_col', None)
				if c_phys is not None and not getattr(cell, 'is_phantom', False):
					sub_text = getattr(cell, 'text', '').strip()
					parent_text = header_labels.get(c_phys, "")
					# Склеиваем родительский заголовок и подзаголовок: "Цена, руб. опт"
					combined_text = f"{parent_text} {sub_text}".strip() if parent_text else sub_text
					header_labels[c_phys] = combined_text

	# Карта семантических зон W3C для сборщика HTML
	parts = [
		('thead', thead_rows, 'th'),
		('tbody', tbody_rows, 'td'),
		('tfoot', tfoot_rows, 'td')
	]
	
	parts_blocks = []
	for p_name, p_rows, tag in parts:
		if not p_rows:
			continue
		
		rows_blocks = []
		for row in p_rows:
			cells_blocks = []
			
			for cell in row.cells:
				cell_class = getattr(cell, 'css_class', 'basic')
				cls_attr = f' class="{cell_class}"' if cell_class != 'basic' else ''
				
				colspan_val = getattr(cell, 'colspan', 1)
				rowspan_val = getattr(cell, 'rowspan', 1)
				
				col_attr = f' colspan="{colspan_val}"' if colspan_val > 1 else ''
				row_attr = f' rowspan="{rowspan_val}"' if rowspan_val > 1 else ''
				
				# === НАШ СНАЙПЕРСКИЙ ВПРЫСК DATA-LABEL ===
				# Прописываем data-label СТРОГО для ячеек тела (tbody) и подвала (tfoot)
				data_label_attr = ""
				if p_name in ['tbody', 'tfoot'] and not getattr(cell, 'is_phantom', False):
					c_phys = getattr(cell, '_phys_col', None)
					if c_phys is not None and c_phys in header_labels:
						# Безопасно экранируем текст шапки для использования внутри HTML-атрибута
						safe_label = escape_html(header_labels[c_phys])
						data_label_attr = f' data-label="{safe_label}"'
				
				# Прогоняем богатый текст ячейки через инлайн-конвейер Марквана
				data_html = exporter_html.render_inline_flow(cell.inlines) if hasattr(cell, 'inlines') else ""
				
				if getattr(cell, 'is_phantom', False):
					cells_blocks.append(f"{gtab}\t\t\t<!--<{tag}></{tag}>-->")
				else:
					# Вставляем наш новый атрибут data_label_attr прямо в тег ячейки!
					cells_blocks.append(f"{gtab}\t\t\t<{tag}{cls_attr}{col_attr}{row_attr}{data_label_attr}>{data_html}</{tag}>")
					
			cells_html = "\n".join(cells_blocks)
			rows_blocks.append(f"""{gtab}\t\t<tr>
{cells_html}
{gtab}\t\t</tr>""")
			
		rows_html = "\n".join(rows_blocks)
		parts_blocks.append(f"""{gtab}\t<{p_name}>
{rows_html}
{gtab}\t</{p_name}>""")

	table_body_html = "\n".join(parts_blocks)

	# === ШАГ 3: ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И ЗAЖAТЫЙ HTML-ШАБЛОН ===
	raw_html = f"""{indent}<figure class="table {incl_class}"{id_attr}>
{figcaption_html}{gtab}<table class="incl-body {incl_class}">
{table_body_html}
{gtab}</table>
{indent}</figure>
"""

	return raw_html.rstrip("\t ")



def render_spoiler_incl(n, indent) -> str:
	"""
	Рендеринг блока спойлера [_ … _].
	Абсолютно чистая геометрия без локальных костылей и ручных фигкапшенов!
	"""
	from html import escape as escape_html

	gtab = indent + "\t"
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	class_attr = n.incl_class
	
	# Извлекаем кликабельный заголовок спойлера (summary)
	title_val = getattr(n, 'title', '')
	summary_text = escape_html(title_val) if title_val else "Показать детали"
	
	# СБOРКA МEТAДAННЫХ ПОДПИСИ (Универсальная микрофункция)
	# Сама соберёт <incl-title>, <incl-descr> и многострочные <incl-comment> !
	figcaption_html = _render_figcaption(n, gtab)
	
	# Вытягиваем мясо внутренних нод (система \n.join сама убрала концевые переносы!)
	body_html = exporter_html.render_nodes_flow(n.nodes, gtab + "\t")
	
	# === ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И ЗAЖAТЫЙ HTML-ШАБЛОН ===
	# Теги закрытия и переходы прижаты впритык, исключая плашки «пробел».
	# Кавычки """ на отдельной строке нативно генерируют финальный \n для Касты Б.
	raw_html = f"""{indent}<details class="spoiler {class_attr}"{id_attr}>
{gtab}<summary>{summary_text}</summary>
{figcaption_html}{gtab}<div class="incl-body {class_attr}">
{body_html}
{gtab}</div>
{indent}</details>
"""

	return raw_html.rstrip("\t ")


def render_group_incl(n, indent) -> str:
	"""
	Рендеринг блока группировки [. … .].
	Используется для создания семантических разделов, карточек или блоков.
	"""
	gtab = indent + "\t"
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	class_attr = n.incl_class
	
	# СБOРКA МEТAДAННЫХ ПОДПИСИ (Универсальная микрофункция)
	figcaption_html = _render_figcaption(n, gtab)
	
	# Вытягиваем мясо внутренних нод
	body_html = exporter_html.render_nodes_flow(n.nodes, gtab + "\t")

	
	# Превращаем класс в  переменные
	spec_class_str, spec_style_attr = parse_adaptive_class(class_attr)

	# === ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И ЗAЖAТЫЙ HTML-ШАБЛОН ===
	raw_html = f"""{indent}<figure class="group {class_attr} {spec_class_str}" {spec_style_attr}  {id_attr}>
{figcaption_html}{gtab}<div class="incl-body">
{body_html}
{gtab}</div>
{indent}</figure>
"""

	return raw_html.rstrip("\t ")


def parse_adaptive_class(raw_class_text: str) -> tuple[str, str]:
	"""
	Парсер адаптивного класса блочного включения.
	Возвращает вспомогательные классы и переменные.
	"""
	# Дефолтные значения осей и стратегии
	maxi, midi, mini = "", "", ""
	strategy_class = ""
	style_attr = ""

	clean_class = raw_class_text.strip().lower()
	
	parts = [p for p in clean_class.split('-') if p]

	if not parts or len(parts) == 1 or parts[0] == 'flex' or len(parts) > 4:
		# Не обрабатываем случаи без класса адаптивности или без указация чисел
		return strategy_class, style_attr  # пустые
	
	elif parts[0] in ['grid', 'col']:
		# Вычисляем обязательный maxi. Проверка на ошибку пользователя.
		if parts[1].isdigit():
			maxi = parts[1]
		else:
			return strategy_class, style_attr  # пустые
		# Вычисляем midi
		if len(parts)>=3:
			if parts[2] == "auto":
				strategy_class = "g-auto"
				if len(parts) == 4:
					mini = parts[3]
					strategy_class = "g-hybrid"
			elif parts[2].isdigit():
				strategy_class = "g-fixed"
				midi = parts[2]
				if len(parts) == 4:
					mini = parts[3]
				else: mini = midi
		else:  # только одна цифра
			midi = maxi
			mini = maxi
			strategy_class = "g-fixed"

	style_attr = f'style="--maxi: {maxi}; --midi: {midi}; --mini: {mini};"'
	
	return strategy_class, style_attr










def render_input_incl(n, indent) -> str:
	"""
	Рендеринг интерактивного блока ввода данных [$ … $].
	Превращается в форму или интерактивное текстовое поле.
	"""
	from html import escape as escape_html

	gtab = indent + "\t"
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	class_attr = n.incl_class
	
	# СБOРКA МEТAДAННЫХ ПОДПИСИ (Наша универсальная микрофункция)
	figcaption_html = _render_figcaption(n, gtab)
	
	# Безопасно вытягиваем сырые строки настроек/плейсхолдеров
	lines = getattr(n, 'raw_lines', getattr(n, 'body_lines', []))
	cleaned_lines = [str(line).rstrip('\r\n') for line in lines]
	raw_content = escape_html("\n".join(cleaned_lines))
	
	# Тотальная защита атрибутов: экранируем заголовок для лейбла
	title_val = getattr(n, 'title', '')
	safe_title = escape_html(title_val) if title_val else ""
	
	# В качестве плейсхолдера формы ввода по спецификации выступает описание ноды
	descr_val = getattr(n, 'description', '')
	safe_placeholder = escape_html(descr_val) if descr_val else ""
	
	# === ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И ЗAЖAТЫЙ HTML-ШАБЛОН ===
	# Переменная {raw_content} внутри textarea прижата к левому краю, 
	# защищая дефолтный текст формы от паразитных табов форматирования Питона!
	raw_html = f"""{indent}<div class="input-block {class_attr}"{id_attr}>
{figcaption_html}{gtab}<label class="input-label">{safe_title}</label>
{gtab}<textarea class="incl-body {class_attr}" placeholder="{safe_placeholder}">
{raw_content}
{gtab}</textarea>
{indent}</div>
"""

	# === НАШ ОФИЦИАЛЬНЫЙ И БРOНИРOВAННЫЙ ВОЗВРАТ РЕЗУЛЬТАТА ===
	# Срезаем случайные правые табы и пробелы (\t ), оставляя нативный \n от кавычек.
	# Теперь никакого NoneType больше не родится!
	return raw_html.rstrip("\t ")







# ^^^
# Вспомогательные функции

def _render_figcaption(node, gtab) -> str:
	"""
	УНИВЕРСАЛЬНЫЙ СБОРЩИК ПОДПИСЕЙ MARKVAN.
	Автоматически вытягивает тип/класс инлайнового комментария 
	и впрыскивает его в CSS-каскад тега <incl-comment>!
	"""
	from html import escape as escape_html

	caption_lines = []
	
	if getattr(node, 'title', ''):
		caption_lines.append(f"{gtab}\t<incl-title>{escape_html(node.title)}</incl-title>")
		
	if getattr(node, 'description', ''):
		caption_lines.append(f"{gtab}\t<incl-descr>{escape_html(node.description)}</incl-descr>")
		
	# ИСПРАВЛEНИE КAРМAШКA: Достаем текст И КЛАССЫ из объектов CommentInline
	node_comments = getattr(node, 'comments', [])
	if node_comments:
		for comment_obj in node_comments:
			# 1. Извлекаем живой текст заметки автора
			if hasattr(comment_obj, 'text'):
				raw_text = comment_obj.text
			elif hasattr(comment_obj, 'body'):
				raw_text = comment_obj.body
			else:
				raw_text = str(comment_obj)
				
			if not str(raw_text).strip():
				continue

			# 2. === НАШ СНАЙПЕРСКИЙ РАДАР КЛАССОВ КОММЕНТАРИЯ ===
			# Проверяем, в каком поле твоя модель хранит тип маркера (///, //!, //?)
			# По канону Ядра это либо .kind, либо .incl_class. Проверяем оба!
			c_kind = getattr(comment_obj, 'kind', getattr(comment_obj, 'incl_class', 'default'))
			c_class = str(c_kind).strip().lower() if c_kind else 'default'
			
			# Страхуем синтаксис от пустых или ложных значений
			if not c_class or c_class == 'none':
				c_class = 'default'

			# 3. Впрыскиваем вычисленный класс прямо в атрибут тега!
			# На выходе получится: <incl-comment class="todo"> или <incl-comment class="issue">
			caption_lines.append(f'{gtab}\t<incl-comment class="{c_class}">{escape_html(str(raw_text).strip())}</incl-comment>')
				
	if caption_lines:
		return f"""{gtab}<figcaption>
{"\n".join(caption_lines)}
{gtab}</figcaption>
"""
	return ""
