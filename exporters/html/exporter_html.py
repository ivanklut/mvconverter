"""
Рендерер дерева AST в формат HTML.
Использует паттерн прямой диспетчеризации методов на основе имен классов моделей.
def export_to_html(self, doc: Document)
	-> def _render_nodes_flow запускает обработку списка объектов
		-> def _Специализированная функция конвертации ноды
			-> def _render_inline_flow для обработки объектов строки.	
"""

from html import escape as escape_html

from utils import ptlog as pt
from markvan.models import *
from exporters import doc_exporter
from exporters.html import exp_h_incl
from exporters.html import exp_h_incl_aggr
from exporters.html import exp_h_highlighter

# на будущее
MARKVAN_TO_HTML_TAG  = {
    "media": 'div',  
    "table": 'table',  
    "p":     'p',      
    "header":     'h2', 
}

# Внутри builder/doc_exporter.py:
CURRENT_DOC_DIR_SLUG = ""  # Общая память для всего процесса экспорта страницы


def export_docbody_to_html(doc: Document) -> str:
	"""
	ГЛАВНАЯ ТОЧКА ВХОДА ЭКСПОРТА HTML (KISS).
	Принимает стерильный Document из Ядра и возвращает монолитный HTML-текст.
	"""
	# Просто запускаем обход корневых нод тела документа! 
	return render_nodes_flow(doc.body.nodes, indent="")


def render_nodes_flow(nodes_list: list, indent: str = "") -> str:
	"""
	Универсальный обходчик нод. Превращает список объектов в HTML-текст.
	"""
	html_list = []
	for node in nodes_list:
		class_name = node.__class__.__name__
	
		# Достаем функцию рендеринга из нашей карты
		current_render_func = RENDER_FUNCTION_MAP.get(class_name)
		
		if current_render_func:
			# Проверяем: если функция пришла из внешнего вынесенного модуля (например, exp_h_incl),
			
			node_html = current_render_func(node, indent)
			


			html_list.append(node_html)
		else:
			pt.wrn(f"Для класса {class_name} не найден HTML-шаблон!", "HTML-Экспортер")
			
	return "\n".join(html_list)




def render_inline_flow(inline_list: list, attachments: list = None) -> str:
	"""
	Конвертер строчных объектов в HTML.
	"""
	# 1. Таблица соответствия логических стилей Марквана и HTML-тегов
	style_tags = {
		'bold': ('<strong>', '</strong>'), 
		'italic': ('<em>', '</em>'),
		'small': ('<small>', '</small>'), 
		'large': ('<span class="text-large">', '</span>'),
		'sup': ('<sup>', '</sup>'), 
		'sub': ('<sub>', '</sub>'),
		'deleted': ('<del>', '</del>'), 
		'added': ('<ins>', '</ins>'),
		'foreign': ('<span class="foreign">', '</span>'),
		'term_mention': ('<span class="term_mention">', '</span>')
	}

	# 2. Таблица соответствия изолированных тех-включений и их тегов
	incl_tags = {
		'code': 'code',
		'math': 'kbd', # Или кастомный тег/класс для формул
		'input': 'kbd',
		'pre': 'span'
	}
	if attachments is None:
		attachments = []

	inline_html_list = []

	title_attr = ""
	download_attr = ""
	target_url = "#"
	
	for el in inline_list:
		# Класс 1: Простой текст
		if isinstance(el, TextSpan):
			# Экранирование символов для HTML
			inline_html_list.append(escape_html(el.text))
			
		# Класс 2: Стили оформлений (Матрёшки с поддержкой вложенности) [INDEX]
		elif isinstance(el, StyledSpan):
			open_tag, close_tag = style_tags.get(el.style_type, ('', ''))
			# РЕКУРСИЯ: отправляем внутренних детей на обход, чтобы раскрыть вложенные стили! 
			inner_html = render_inline_flow(el.children)
			inline_html_list.append(f"{open_tag}{inner_html}{close_tag}")
			
		# Класс 3: Интерактивная сноска (С автонумерацией, мануальным и символьным режимом) 
		elif isinstance(el, FootnoteSpan):
			# 1. Извлекаем итоговый текстовый маркер, который мы так долго вычисляли!
			# Если агрегатор почему-то его не посчитал (фолбек), берем сырой raw_ftn_id
			num = getattr(el, 'res_ftn_id', None) or getattr(el, 'raw_ftn_id', '*')
			
			# 2. Вычисляем тип идентификатора ("auto", "manual", "symbol"), чтобы ID на странице были уникальными
			id_type = getattr(el, 'id_type', 'symbol')
			
			# =====================================================================
			# 🪓 ВЫКУСЫВАЕМ ТЕКСТ СНОСКИ ДЛЯ ВСПЛЫВАЮЩЕЙ ПОДСКАЗКИ (KISS!)
			# =====================================================================
			tooltip_html_attr = ""
			
			# Проверяем, привязал ли наш утренний Агрегатор контент сноски к этой ссылке
			footnote_node = getattr(el, 'footnote_content', None)
			if footnote_node and hasattr(footnote_node, 'text') and footnote_node.text:
				# Экранируем двойные кавычки в тексте, чтобы HTML-атрибут data-tooltip не сломался
				safe_text = escape_html(footnote_node.text)
				tooltip_html_attr = f' data-tooltip="{safe_text}"'
			# =====================================================================

			# Собираем красивый интерактивный тег с уникальными ID якорей
			# id="ftn-ref-..." — это точка, откуда пришел читатель (для обратной стрелочки из подвала)
			# href="#ftn-..." — это точка в подвале, куда перейдет читатель при клике
			inline_html_list.append(
				f'<sup class="ftn-marker" id="ftn-ref-{num}" {tooltip_html_attr}>'
				f'<a href="#ftn-text-{num}">{num}</a>'
				f'</sup>'
			)


		# Класс 4: Гиперссылка <[ … ]> или концевая ссылка строки
		elif isinstance(el, LinkSpan):
			if el.link is not None:
				
				# ИСПРАВЛЕНИЕ: Вызываем калибратор БЕЗ второго аргумента!
				# Он сам заберёт правильный base_path (../../) из памяти doc_exporter.py
				target_url = doc_exporter.get_web_path(el.link)

				safe_title = escape_html(el.link.title)
				title_attr = f' title="{safe_title}"' if safe_title else ''
				link_type = getattr(el.link, "type", "local")
				download_attr = " download" if getattr(el.link, "type", "") == "download" else ""
		
			else:
				pass
			
			if hasattr(el, 'inline_elements') and el.inline_elements:
				inner_body = render_inline_flow(el.inline_elements, attachments)
			else:
				inner_body = target_url
				
			inline_html_list.append(f'<a href="{target_url}" class="text-link"{title_attr}{download_attr}>{inner_body}</a>')
			
		# Класс 5: Технические сырые включения (код, формулы, пре)
		elif isinstance(el, InlineIncl):
			# 1. СТРОЧНЫЙ PRE: Заворачиваем в span и экранируем контент
			if el.incl_type == 'pre':
				class_attr = f' class="inline-incl pre {el.incl_class}"' if el.incl_class else ' class="inline-incl pre"'
				inline_html_list.append(f'<span{class_attr}>{escape_html(el.text)}</span>')
			
			# 2. СТРОЧНЫЙ КОД (ВЫПРЯМЛЯЕМ! Направляем в хайлайтер для подсветки синтаксиса)
			elif el.incl_type == 'code':
				t_name = incl_tags.get(el.incl_type, 'code')
				class_attr = f' class="inline-incl {el.incl_class} pygments"' if el.incl_class else ' class="inline-incl"'
				
				# Прогоняем код через твой вынесенный модуль хайлайтера Pygments
				highlight_text = exp_h_highlighter.highlight_inline_code(el.text, el.incl_class)
				inline_html_list.append(f'<{t_name}{class_attr}>{highlight_text}</{t_name}>')
			
			# 3. СТРОЧНАЯ МАТЕМАТИКА (ЖЕСТКОЕ ПРАВИЛО: отдаем кристально чистую сырую строку!)
			elif el.incl_type == 'math':
				t_name = incl_tags.get(el.incl_type, 'span')
				class_attr = f' class="inline-incl {el.incl_class}"' if el.incl_class else ' class="inline-incl"'
				
				# КАТЕГОРИЧЕСКИ НЕЛЬЗЯ экранировать или подсвечивать TeX-код на бэкенде!
				# KaTeX и MathJax на фронте должны прочитать чистые бэкслеши и знаки дробей.
				inline_html_list.append(f'<{t_name}{class_attr}>{el.text}</{t_name}>')

			elif el.incl_type == 'spoiler':
				t_name = incl_tags.get(el.incl_type, 'span')
				class_attr = f' class="inline-incl spoiler-inline {el.incl_class}"' if el.incl_class else ' class="inline-incl spoiler-inline"'
				# pt.deb(f'<{t_name}{class_attr} role="button" tabindex="0" onclick="this.classList.toggle(\'revealed\')>{el.text}</{t_name}>')
				inline_html_list.append(f'<{t_name}{class_attr} role="button" tabindex="0" onclick="this.classList.toggle(\'revealed\')">{el.text}</{t_name}>')

				# return f'<span class="spoiler-inline" role="button" tabindex="0" onclick="this.classList.toggle(\'revealed\')">{n.text}</span>'
				
			else:
				# 4. Для остальных (input, кустарные теги) оставляем безопасный дефолт
				t_name = incl_tags.get(el.incl_type, 'span')
				class_attr = f' class="inline-incl {el.incl_class}"' if el.incl_class else ""
				inline_html_list.append(f'<{t_name}{class_attr}>{escape_html(el.text)}</{t_name}>')


			
		# Класс 6: Ленивая переменная (Резервный случай) [INDEX]
		elif isinstance(el, VariableSpan):
			# Если Агрегатор почему-то её пропустил, выводим исходный текст, спасая верстку [INDEX]
			inline_html_list.append(f"{{{{{el.key}}}}}")
					# Класс 7: ТВОИ СЕМАНТИЧЕСКИЕ СТРОЧНЫЕ КОММЕНТАРИИ НА ПОЛЯХ! [INDEX]

		elif isinstance(el, CommentInline):
			# Маппинг внутренних типов в человеческие CSS-классы

			comment_classes = {
				'remark': 'comment remark',   # Простая заметка ///
				'issue': 'comment issue', # Проблема/Спорный момент //?
				'todo': 'comment todo'    # Задача //!
			}
			c_class = comment_classes.get(el.kind, 'comment notdef')
			
			# Экранируем стрелочки внутри текста комментария для безопасности XML/HTML
			clean_comment = escape_html(el.text)
			
			# Возвращаем тег <aside> (заметка на полях/сторонняя информация) [INDEX]
			inline_html_list.append(f'<small class="{c_class}" title="Режим черновика">{clean_comment}</small>')


	return "".join(inline_html_list)



# """
# МЕТОДЫ ОБЪЕКТОВ

# ===
# Элементы тела документа (Nodes) (кроме блочных включений)

def render_section(n, indent) -> str:
	"""Обработчик секций-матрешек с семантическим фильтром по типу заголовка!"""
	next_indent = indent + "\t"
	inner_html = render_nodes_flow(n.nodes, next_indent)
	
	heading_kind = ""		
	if n.nodes and n.nodes[0].__class__.__name__ == 'Heading':
		heading_kind = n.nodes[0].kind

	if heading_kind in ['part', 'chapter']:
		return f'{indent}<section class="section-{heading_kind}">\n{inner_html}{indent}</section>\n'
	return inner_html

def render_endsection(n, indent) -> str:
	"""Линейный разделитель между секциями."""
	return f'{indent}<hr class="section-separator" />\n'

def render_heading(n, indent) -> str:
	"""
	Рендеринг заголовка. Абсолютно чистая системная геометрия!
	Полностью адаптирован под Касту А (без концевого \n).
	"""
	from html import escape as escape_html

	# Константы тегов разметки Марквана
	mv_h_tags = {
		'part': 'h-part',
		'chapter': 'h-chapter',
		'header': 'h2', 
		'subheader': 'h3', 
		'th3': 'h4', 
		'th4': 'h5', 
		'th5': 'h6', 
		'th6': 'h7',
	}
	
	id_attr = f' id="{n.id}"' if getattr(n, 'id', '') else ""
	tag_attr = mv_h_tags.get(n.kind, 'h2')
	class_attr = f' class="{n.kind}"' if n.kind else ""

	# --- СБОРКА ИЗОЛИРОВАННОГО НАДЗАГОЛОВКА (SUPRA)
	supra_html = ""
	if getattr(n, 'supra', ''):
		# Надзаголовок встаёт ровно на свой этаж с отступом indent
		supra_html = f'<{tag_attr}-supra>{escape_html(n.supra)}</{tag_attr}-supra>\n{indent}'

	# Скармливаем заголовок инлайн-обходчику (курсив, жирность, инлайн-код)
	heading_body = render_inline_flow(n.inlines) if hasattr(n, 'inlines') and n.inlines else escape_html(getattr(n, 'text', ''))
	#! Наверное запрещу что-нибудь вставлять в заголовок. Хотя ссылки в обратку могут быть полезны...
	
	# === ТВОЙ ИДЕАЛЬНО НАГЛЯДНЫЙ И КРАСИВЫЙ HTML-ШАБЛОН ЗАГОЛОВКА ===
	# Обрати внимание: закрывающие кавычки """ стоят ВПЛОТНУЮ к закрывающему тегу!
	# Благодаря этому тройные кавычки НЕ создадут автоматический перенос \n в конце,
	# что делает заголовок идеальным, суверенным блоком Касты А!
	raw_html = f"""{indent}{supra_html}<{tag_attr}{id_attr}{class_attr}>{heading_body}</{tag_attr}>"""
	
	# Срезаем случайные правые табы и пробелы, возвращая чистый сухой HTML-блок
	return raw_html.rstrip("\t ")


def render_pausehead(n, indent) -> str:
	"""Заголовок-пауза ~~~"""
	# Заменили \t на честный динамический indent
	text_content = escape_html(n.text) if n.text else ""
	return f'{indent}<div class="pause-head">{text_content}</div>'

def render_paragraph(n, indent) -> str:
	"""
	Рендеринг абзаца прозы Маркван.
	"""
	# Избавились от мертвого target_link. Параграф теперь кристально чист.
	body = render_inline_flow(n.inlines, getattr(n, 'attachments', []))

	return f"{indent}<p>{body}</p>"


def render_termdef(n, indent) -> str:
	"""
	Семантическая пара Термин-Определение в одну чистую строку.
	Использует новые плоские массивы term_inlines и definition_inlines.
	"""
	# Прогоняем обе части через инлайн-обходчик. Это дает тотальную свободу стилей!
	term_html = render_inline_flow(n.term_inlines)
	def_html = render_inline_flow(n.definition_inlines)

	# Идеальный, легкий HTML-вывод без промежуточных контейнеров
	return f"{indent}<dt>{term_html}</dt> <dd>{def_html}</dd>"

def render_contextpair(n, indent) -> str:
	"""
	Семантический рендерер контекстных пар Предикат:Зависимый элемент.
	Автоматически пробрасывает правильный уровень табов во все вложенные ноды!
	"""
	inner_indent = indent + "\t"
	
	# Предикат рендерится как инлайн-поток внутри своего блока
	pred_html = render_inline_flow(n.predicate_node.inlines) if hasattr(n.predicate_node, 'inlines') else ""
	
	dep_html = ""
	if n.dependent_node:
		dep_class = n.dependent_node.__class__.__name__
		dep_handler = RENDER_FUNCTION_MAP.get(dep_class)
		if dep_handler:
			dep_html = dep_handler(n.dependent_node, inner_indent)
		else:
			pt.wrn(f"Внутри контекстной пары не найден шаблон для зависимого класса {dep_class}", "HTML-Экспортер")

	raw_html = f"""<div class="context-pair">
<div class="predicate">{pred_html}</div>
{dep_html}</div>
"""

	return indent + raw_html


def render_listblock(n, indent) -> str:
	"""
	Универсальный рендерер списков Маркван.
	Использует всю мощь рекурсивных sub_items. Код стал прозрачным как стекло!
	"""
	# Выбираем правильный тег на основе типа списка, который зафиксировало Ядро
	base_tag = "ul" if n.kind in ["auto_numbered", "manual_numbered"] else "ul"
	
	html_out = []
	html_out.append(f"{indent}<{base_tag} class=\"text-list list-{n.kind}\">\n")
	
	next_indent = indent + "\t"
	
	for item in n.items:

		# Рендерим текстовое содержимое самого пункта
		# Рендерим текстовое содержимое самого пункта, ОБЯЗАТЕЛЬНО передавая мешок вложений!
		if hasattr(item, 'inlines') and item.inlines:
			inline_html = render_inline_flow(item.inlines, getattr(item, 'attachments', []))
		else:
			inline_html = escape_html(item.text)

		
		# Заныриваем в мешок sub_items для сбора вложенного контента (прозы или подсписков)!
		inner_content_html = ""
		if hasattr(item, 'sub_items') and item.sub_items:
			# # Собираем все внутренности на один таб глубже
			# inner_pieces = []
			# for sub_node in item.sub_items:
			# 	sub_class = sub_node.__class__.__name__
			# 	sub_handler = RENDER_FUNCTION_MAP.get(sub_class)
			# 	if sub_handler:
			# 		# Рекурсивный вызов! Сам отрендерит и подсписок, и абзац прозы с правильным сдвигом!
			# 		inner_pieces.append(sub_handler(sub_node, next_indent + "\t"))
			
			# if inner_pieces:
			# 	inner_content_html = "\n" + "".join(inner_pieces).rstrip("\n") + f"\n{next_indent}"

			inner_content_html = "\n" + render_nodes_flow(item.sub_items, next_indent + "\t").rstrip("\n") + f"\n{next_indent}"

		# Формируем атрибут data-label, если у пункта есть ручной маркер manual_number
		if hasattr(item, 'manual_number') and item.manual_number:
			html_out.append(f'{next_indent}<li class="custom-marker" data-label="{item.manual_number}">{inline_html}{inner_content_html}</li>\n')
		else:
			html_out.append(f'{next_indent}<li>{inline_html}{inner_content_html}</li>\n')
			
	html_out.append(f"{indent}</{base_tag}>\n")
	return "".join(html_out)


def render_groupspacer(n, indent) -> str:
	"""
	Рендеринг пустого маркера ячейки .[]. (GroupSpacer).
	Выплёвывает стерильный плоский блок-заглушку для удержания шага CSS Grid.
	"""
	# Выдаем чистый скрытый тег без лишних переносов строк внутри
	return f'{indent}<div class="grid-cell empty"></div>'


# def render_spoiler_inline(n, indent) -> str:
# 	"""Строчное скрывающее включение (спойлер) _[ текст ]_."""

# 	# Идеальный, легкий HTML-вывод без промежуточных контейнеров
# 	return f'<span class="spoiler-inline" role="button" tabindex="0" onclick="this.classList.toggle(\'revealed\')">{n.text}</span>'


RENDER_FUNCTION_MAP = {
	# --- Функции, которые пока остаются жить прямо в этом файле ---
	'Section':                  render_section,
	'EndSection':               render_endsection,
	'PauseHead':                render_pausehead,
	'Heading':                  render_heading,
	'Paragraph':                render_paragraph,
	'ContextPair':              render_contextpair,
	'TermDef':                  render_termdef,
	'ListBlock':               	render_listblock,
	# 'SpoilerInline':            render_spoiler_inline,

	# --- Блочные включения [X ... X] (Вынесены в модуль exp_h_incl) ---
	'TextIncl':                 exp_h_incl.render_text_incl,
	'CommentIncl':              exp_h_incl.render_comment_incl,
	'PreIncl':                  exp_h_incl.render_pre_incl,
	'CodeIncl':                 exp_h_incl.render_code_incl,
	'FormulaIncl':              exp_h_incl.render_formula_incl,
	'MediaIncl':                exp_h_incl.render_media_incl,
	'TableIncl':                exp_h_incl.render_table_incl, 
	'SpoilerIncl':              exp_h_incl.render_spoiler_incl,
	'GroupingIncl':             exp_h_incl.render_group_incl,
	"GroupSpacer":              render_groupspacer,
	'InputIncl':                exp_h_incl.render_input_incl,

	# --- Динамические включения агрегации {§X ... §} (В модуле exp_h_incl_aggr) ---
	'TableOfContents':          exp_h_incl_aggr.render_tableofconten,
	'SpoilerCollectionBlock':   exp_h_incl_aggr.render_spoilercollecsionblock,
	'GlossaryBlock':            exp_h_incl_aggr.render_glossaryblock,             
	'FootnotesCollectionBlock': exp_h_incl_aggr.render_footnotescollectionblock,
	'RawCodeBlock':             exp_h_incl_aggr.render_rawcodeblock
}