"""
Модуль exporters/exporter_ast.py
Минималистичный экспортер абстрактного синтаксического дерева (AST) Маркван.
Максимально очищен от визуального шума для легкого восприятия глазами.
"""

from markvan.models import (
	Document, Section, Heading, Paragraph, render_termdef, 
	ContextPair, ListBlock, ListItem, PauseHead, EndSection, TableOfContents, TextIncl, RawCodeBlock
)

def export_to_ast(doc: Document) -> str:
	"""
	Принимает дерево Document, формирует компактную текстовую 
	схему и возвращает её в виде одной сплошной строки.
	"""
	lines = []
	lines.append("=== AST TREE EXPORT ===")
	lines.append(f"Metadata variables count: {len(doc.metadata)}")
	lines.append("___")
	
	if doc.title:
		lines.append(f"├── Title | {doc.title.name}")
		
	# Выводим корень (Нулевой уровень) без отступа
	lines.append("0")
	
	# ТВОЕ ИСПРАВЛЕНИЕ: передаем пустую строку "", чтобы первый уровень веток шел строго от левого края!
	_print_section_ast(doc.body, "", lines)
	
	return "\n".join(lines)


def _get_paragraph_preview(paragraph_node: Paragraph, max_len: int = 40) -> str:
	"""Рекурсивно собирает голый text из инлайн-элементов для превью."""
	text_pieces = []
	def _collect(elements):
		for el in elements:
			if hasattr(el, 'text') and el.text:
				text_pieces.append(el.text)
			elif hasattr(el, 'children') and el.children:
				_collect(el.children)
	_collect(paragraph_node.inlines)
	full_text = "".join(text_pieces).strip()
	if len(full_text) > max_len:
		return full_text[:max_len] + "..."
	return full_text if full_text else "[Пустая строка]"


def _print_section_ast(section: Section, indent: str, lines: list):
	"""
	Прямой хронологический обход единого потока нод и подсекций.
	Выводит данные в ультра-компактном формате без лишних кавычек.
	"""
	for i, node in enumerate(section.nodes):
		is_last = (i == len(section.nodes) - 1)
		branch = "└── " if is_last else "├── "
		
		if isinstance(node, Section):
			# Выводим только число уровня
			lines.append(f"{indent}{branch}{node.level}")
			
			# РЕКУРСИЯ: Уходим вглубь матрёшки контента
			next_indent = indent + ("    " if is_last else "│   ")
			_print_section_ast(node, next_indent, lines)
			
		elif isinstance(node, Heading):
			h_id = f" #{node.id}" if node.id else ""
			if node.supra:
				lines.append(f"{indent}{branch}Heading | {node.kind}{h_id} ({node.supra} | {node.text})")
			else:
				lines.append(f"{indent}{branch}Heading | {node.kind}{h_id} ({node.text})")


			
		elif isinstance(node, Paragraph):
			# ТВОЕ ИСПРАВЛЕНИЕ: Компактный формат без кавычек
			preview = _get_paragraph_preview(node)
			lines.append(f"{indent}{branch}Paragraph ({preview})")
			
		elif isinstance(node, EndSection):
			lines.append(f"{indent}{branch}EndSection (___)")
			
		elif isinstance(node, render_termdef):
			# выводим TermPair в одну красивую строку контента
			preview = _get_paragraph_preview(node.definition)
			lines.append(f"{indent}{branch}TermPair ({node.term} | {preview})")

			
		elif isinstance(node, ContextPair):
			# Пишем имя родительского класса
			lines.append(f"{indent}{branch}ContextPair")
			
			# Вычисляем правильный графический отступ для детей контекстной пары
			sub_indent = indent + ("    " if is_last else "│   ")
			
			# 1. Выводим веточку Предиката
			pred_preview = _get_paragraph_preview(node.predicate_node, max_len=20)
			lines.append(f"{indent}{sub_indent}├── Predicate: ({pred_preview})")
			
			# 2. Выводим веточку Зависимого элемента через знак равенства
			dep_name = node.dependent_node.__class__.__name__
			
			# Делаем красивое превью, если зависимым элементом оказался обычный абзац
			if isinstance(node.dependent_node, Paragraph):
				dep_preview = _get_paragraph_preview(node.dependent_node, max_len=20)
				lines.append(f"{indent}{sub_indent}└── Dependent = Paragraph ({dep_preview})")
			else:
				# Если там список, таблица или код — просто пишем имя класса, как у тебя в примере
				lines.append(f"{indent}{sub_indent}└── Dependent = {dep_name}")
				
				# Если это список, и мы хотим заглянуть в его пункты, мы можем рекурсивно 
				# вызвать принтер для списков прямо сюда, но пока оставим лаконично!

			
		elif isinstance(node, ListBlock):
			# Компактный формат для заголовка списка
			lines.append(f"{indent}{branch}ListBlock | {node.kind} (items: {len(node.items)})")
			
			# Рассчитываем правильный иерархический отступ для пунктов списка
			sub_indent = indent + ("    " if is_last else "│   ")
			
			for sub_idx, item in enumerate(node.items):
				is_last_item = (sub_idx == len(node.items) - 1)
				sub_branch = "└── " if is_last_item else "├── "
				
				# Твоё каноническое правило: весь контент строго в круглых скобках без кавычек!
				# Ограничиваем превью текста до 25 символов для компактности
				preview = item.text[:25].strip()
				if len(item.text) > 25:
					preview += "..."
					
				lines.append(f"{indent}{sub_indent}{sub_branch}ListItem | lvl={item.level} ({preview})")
		elif isinstance(node, TextIncl):
			# Формируем компактную паспортную строку умного текстового блока
			h_id = f" #{node.id}" if node.id else ""
			h_cls = f" class={node.incl_class}" if node.incl_class else ""
			h_ttl = f" [{node.title}]" if node.title else ""
			h_dsc = f" desc:({node.description})" if node.description else ""
			
			lines.append(f"{indent}{branch}TextIncl{h_id}{h_cls}{h_ttl}{h_dsc}")
			
			# РЕКУРСИЯ: заглядываем внутрь матрешки и выводим её внутренний хронологический поток нод!
			next_indent = indent + ("    " if is_last else "│   ")
			_print_section_ast(node, next_indent, lines)
			
		elif isinstance(node, TableOfContents):
			# Выводим параметры блока агрегации оглавления
			h_id = f" #{node.id}" if node.id else ""
			h_ttl = f" ({node.title})" if node.title else ""
			# Показываем, какой технический лимит глубины записался в метаданных блока
			h_lim = f" limit={node.limit_level}" if hasattr(node, 'limit_level') else ""
			
			lines.append(f"{indent}{branch}TableOfContents{h_id}{h_lim}{h_ttl}")
			
		elif isinstance(node, RawCodeBlock):
			# Компактный вывод для инъекций сырого технического кода {$ ... $}
			lines.append(f"{indent}{branch}RawCodeBlock (lines: {len(node.raw_lines)})")

				
		elif isinstance(node, PauseHead):
			lines.append(f"{indent}{branch}PauseHead")
			
		else:
			lines.append(f"{indent}{branch}{node.__class__.__name__}")
