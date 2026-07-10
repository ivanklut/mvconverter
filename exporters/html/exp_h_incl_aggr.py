# ***
# Включения результатов агрегации и динамического встраивания {X … X}

from exporters.html.exporter_html import escape_html
from exporters.html import exporter_html
from utils import ptlog as pt

def render_tableofconten(n, indent) -> str:
	"""Рендеринг автоматического оглавления книги {§toc … §}"""
	id_attr = f' id="{n.id}"' if hasattr(n, 'id') and n.id else ""
	gtab = indent + "\t"
	
	# Заголовки (h) содержат богатый текст внутри .inlines, прогоняем через обходчик инлайнов!
	links_pieces = []
	if hasattr(n, 'items') and n.items:
		for h in n.items:
			heading_id = h.id if getattr(h, 'id', '') else ''
			heading_text = exporter_html._render_inline_flow(h.inlines) if hasattr(h, 'inlines') else escape_html(getattr(h, 'text', ''))
			links_pieces.append(f"{gtab}\t<li><a href=\"#{heading_id}\">{heading_text}</a></li>\n")
			
	links_html = "".join(links_pieces)
	safe_title = escape_html(n.title) if (hasattr(n, 'title') and n.title) else "Содержание"
	
	raw_html = f"""{indent}<nav class="table-of-contents {n.incl_class}"{id_attr}>
{gtab}<h3>{safe_title}</h3>
{gtab}<ul>
{links_html}{gtab}</ul>
{indent}</nav>
"""
	return raw_html.rstrip("\t\n") + "\n"


def render_spoilercollecsionblock(n, indent) -> str:
	"""Рендеринг коллекции агрегированных спойлеров {§spoiler … §}."""
	id_attr = f' id="{n.id}"' if hasattr(n, 'id') and n.id else ""
	gtab = indent + "\t"
	
	inner_html = exporter_html.render_nodes_flow(n.items, gtab) if hasattr(n, 'items') else ""
	safe_title = escape_html(n.title) if (hasattr(n, 'title') and n.title) else "Сборник спойлеров"
	
	raw_html = f"""{indent}<div class="spoiler-collection {n.incl_class}"{id_attr}>
{gtab}<h3>{safe_title}</h3>
{inner_html}{indent}</div>
"""
	return raw_html.rstrip("\t\n") + "\n"


def render_glossaryblock(n, indent) -> str:
	"""Рендеринг автоматического глоссария терминов {§glossary … §}."""
	id_attr = f' id="{n.id}"' if hasattr(n, 'id') and n.id else ""
	gtab = indent + "\t"
	
	terms_html = ""
	if hasattr(n, 'items') and n.items:
		terms_html = "".join(exporter_html.render_termdef(t, gtab + "\t") for t in n.items)
		
	safe_title = escape_html(n.title) if (hasattr(n, 'title') and n.title) else "Словарь терминов"
	raw_html = f"""{indent}<section class="glossary {n.incl_class}"{id_attr}>
{gtab}<h3>{safe_title}</h3>
{gtab}<dl class="glossary-list">
{terms_html}{gtab}</dl>
{indent}</section>
"""
	return raw_html.rstrip("\t\n") + "\n"




def render_footnotescollectionblock(n, indent) -> str:
	"""
	Рендеринг подвала сносок {§footnotes … §} по нашему каскадному канону.
	"""
	gtab = indent + "\t"
	lines_html = ""
	
	# СНОСКИ ЛЕЖАТ СТРОГО ВНУТРИ САМОЙ НОДЫ БЛОКА! (И явной, и фантомной)
	if hasattr(n, 'items') and n.items:
		for ftn in n.items:
			# Извлекаем тип и итоговый вычисленный маркер (1, 2, * и т.д.)
			num = getattr(ftn, 'res_ftn_id', '*')
			id_type = getattr(ftn, 'id_type', 'symbol')
			
			# Чистый текст сноски (защищаем от спецсимволов)
			safe_footnote_text = escape_html(getattr(ftn, 'text', ''))
			
			# Перекрёстный прыжок: сопрягаем ID и href с инлайновыми подсказками текста
			# id="fn-..." — это точка сноски в подвале страницы
			# href="#ftn-ref-..." — это обратный прыжок к циферке в тексте параграфа
			lines_html += f"""{gtab}\t<p id="ftn-text-{num}">
{gtab}\t\t<sup class="ftn-text-marker"><a href="#ftn-ref-{num}">{num}</a></sup>
{gtab}\t\t<span>{safe_footnote_text}</span>
{gtab}\t</p>\n"""
	
	# Блок 
	raw_html = f"""{indent}<div class="footnotes">
{gtab}<hr class="ftn">
{lines_html}{indent}</div>
"""
	return raw_html.rstrip("\t\n") + "\n"


def render_rawcodeblock(n, indent) -> str:
	"""
	Прямая инъекция кода {& … &}.
	Выплёвывает сырые строки автора в HTML-файл абсолютно без изменений!
	"""
	lines = getattr(n, 'raw_lines', getattr(n, 'body_lines', []))
	raw_content = "".join(f"{indent}{line}\n" for line in lines)
	return raw_content


