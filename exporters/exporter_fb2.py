import base64
import os
from utils import ptlog as pt
from markvan.models import Document

class FB2Exporter:
	def __init__(self):
		"""
		Личный, изолированный реестр FB2-экспортера.
		Связывает имена классов нод AST со СВОИМИ собственными XML-методами!
		"""
		self.render_map = {
			'Section': self._Section,
			'Heading': self._Heading,
			'Paragraph': self._Paragraph,
			'ListItem': self._ListItem,       # Добавили поддержку пунктов списков в FB2
			'EndSection': self._EndSection,
			'MediaIncl': self._MediaIncl       # РАСКОММЕНТИРОВАЛИ И ПОДКЛЮЧИЛИ КАРТИНКИ!
		}

	# =====================================================================
	# ЗЕРКАЛЬНЫЕ XML-МЕТОДЫ ОБРАБОТЧИКОВ БЛОКОВ (строго на табах)
	# =====================================================================

	def _Section(self, n, indent) -> str:
		"""Каждая подсекция AST-дерева превращается в канонический тег <section>"""
		next_indent = indent + "  "
		inner_xml = self._render_nodes_flow(n.nodes, next_indent)
		return f"{indent}<section>\n{inner_xml}{indent}</section>\n"
	
	def _EndSection(self, n, indent) -> str:
		"""Линейный разделитель ___ превращается в пустую строку по спецификации FB2"""
		return f"{indent}<empty-line/>\n"

	def _Heading(self, n, indent) -> str:
		"""Рендеринг заголовков главы по правилам FB2"""
		clean_text = n.text.replace("&", "&amp;").replace("<", "&lt;")
		clean_supra = n.supra.replace("&", "&amp;").replace("<", "&lt;") if n.supra else ""
		
		supra_p = f"<p>{clean_supra}</p>\n  " if clean_supra else ""
		
		raw_xml = f"""<title>
  {supra_p}<p>{clean_text}</p>
</title>
"""
		return indent + raw_xml.replace("\n", "\n" + indent).rstrip(indent)

	def _Paragraph(self, n, indent) -> str:
		"""Рендеринг обычного текстового абзаца"""
		clean_text = n.text.replace("&", "&amp;").replace("<", "&lt;") if hasattr(n, 'text') and n.text else ""
		return f"{indent}<p>{clean_text}</p>\n"

	def _ListItem(self, n, indent) -> str:
		"""Рендеринг пунктов списков (в FB2 выводим как абзацы с буллитом)"""
		clean_text = n.text.replace("&", "&amp;").replace("<", "&lt;") if hasattr(n, 'text') and n.text else ""
		return f"{indent}<p>• {clean_text}</p>\n"

	def _MediaIncl(self, n, indent) -> str:
		"""
		Рендерер медиаблоков [[ ... ]] для FB2.
		Извлекает чистые имена файлов и генерирует валидные XML-ссылки на бинарники!
		"""
		res = []
		if hasattr(n, 'items') and n.items:
			for item in n.items:
				if hasattr(item, 'src_path') and item.src_path:
					# Извлекаем путь к файлу (наш Агрегатор гарантирует, что он чистый и относительный!)
					img_path = item.src_path.address if hasattr(item.src_path, 'address') else str(item.src_path)
					if img_path:
						# Извлекаем чистое имя файла (например, pic01.jpg) для ID вставки
						img_id = os.path.basename(img_path)
						res.append(f'{indent}<p><image l:href="#{img_id}"/></p>\n')
		return "".join(res)

	def _build_description(self, doc: Document) -> str:
		"""Генерирует метаинформацию книги из глобального словаря metadata"""
		metadata = getattr(doc, 'metadata', {})
		author_name = metadata.get("author", "Неизвестный автор")
		book_title = metadata.get("title", "Без названия")
		
		author_parts = author_name.split(maxsplit=1)
		first_name = author_parts[0] if author_parts else "Неизвестный"
		last_name = author_parts[1] if len(author_parts) > 1 else ""
		
		last_name_xml = f"<last-name>{last_name}</last-name>" if last_name else ""

		return f"""  <description>
	<title-info>
	  <genre>prose</genre>
	  <author>
		<first-name>{first_name}</first-name>
		{last_name_xml}
	  </author>
	  <book-title>{book_title}</book-title>
	  <lang>ru</lang>
	</title-info>
  </description>"""

	def _render_nodes_flow(self, nodes_list: list, indent: str) -> str:
		"""Универсальный хронологический конвейер вызова методов"""
		chunks = []
		for n in nodes_list:
			class_name = n.__class__.__name__
			handler = self.render_map.get(class_name)
			
			if handler:
				html_chunk = handler(n, indent)
				if html_chunk is not None:
					chunks.append(html_chunk)
				else:
					pt.wrn(f"Метод {handler.__name__} для класса {class_name} вернул None!", "FB2-Экспортер")
			else:
				pt.wrn(f"Для класса {class_name} не найден FB2-шаблон!", "FB2-Экспортер")
				
		return "".join(chunks)

	def _collect_binary(self, doc, vfs) -> str:
		"""Использует готовую корзину ассетов от Агрегатора и кодирует в Base64"""
		import base64
		binaries = []
		found_files = set()
		
		if not hasattr(doc, 'linked_assets') or not doc.linked_assets:
			return ""
			
		unique_assets = list(set(doc.linked_assets))
		
		for img_path in unique_assets:
			img_name = os.path.basename(img_path).split(' ')[0]
			
			if img_name not in found_files:
				# === НАШЕ ГЛАВНОЕ ИСПРАВЛЕНИЕ: Читаем байты через стандартный open! ===
				real_img_path = vfs.get_real_media_path(img_path)
				
				if real_img_path and os.path.exists(real_img_path):
					try:
						with open(real_img_path, 'rb') as f:
							raw_bytes = f.read()
							
						if not raw_bytes:
							continue
							
						encoded = base64.b64encode(raw_bytes).decode('utf-8')
						
						ext = img_name.split('.')[-1].lower()
						mime = f"image/{ext}".replace('jpg', 'jpeg')
						if ext == 'png': 
							mime = "image/png"
						
						binaries.append(f'  <binary id="{img_name}" content-type="{mime}">{encoded}</binary>')
						found_files.add(img_name)
						
						pt.deb(f"[FB2-Binary] Картинка успешно вшита в книгу: {img_name}")
					except Exception as e:
						pt.err(f"Ошибка Base64-кодирования картинки {img_name}: {e}")
				else:
					pt.wrn(f"Файл картинки отсутствует на диске по пути VFS: {img_path}")
					
		return "\n".join(binaries)

	def export_to_fb2(self, doc: Document, vfs) -> str:
		"""Главная точка входа FB2-экспортера"""
		xml = []
		xml.append('<?xml version="1.0" encoding="utf-8"?>')
		xml.append('<FictionBook xmlns="http://gribuser.ru" xmlns:l="http://w3.org">')

		xml.append(self._build_description(doc))
		xml.append('  <body>')
		xml.append(self._render_nodes_flow(doc.body.nodes, indent="    "))
		xml.append('  </body>')
		xml.append(self._collect_binary(doc, vfs))
		xml.append('</FictionBook>')
		
		return "\n".join(xml)
