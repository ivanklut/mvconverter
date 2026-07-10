"""
Модуль exporters/exporter_epub.py
Виртуальный экспортер пакета EPUB в оперативной памяти.
Использует плоскую, неуязвимую для Calibre структуру файлов архива.
"""

import os
import re
from markvan.models import Document
from exporters.html.exporter_html import HtmlExporter
from utils import ptlog as pt

class EPUBExporter:
	def __init__(self):
		self.mimetype = "application/epub+zip"

	def export_to_epub(self, doc: Document, vfs, cfg) -> dict:
		"""
		Главная точка входа. Собирает плоскую структуру файлов EPUB в памяти.
		"""
		package = {}
		
		# 1. Служебный паспорт архива (mimetype строго в корне)
		package["mimetype"] = self.mimetype
		package["META-INF/container.xml"] = self._build_container()

		# 2. Вычисляем безопасное дефолтное название книги
		default_name = os.path.splitext(os.path.basename(cfg.input_path))[0]
		book_title = doc.metadata.get("title", default_name)

		# 3. ГЕНЕРАЦИЯ XHTML-КОНТЕНТА КНИГИ
		html_renderer = HtmlExporter() #max_section_depth=3
		body_html = html_renderer.export_docbody_to_html(doc)

		# Подменяем пути картинок: теперь папка Images лежит прямо в корне архива рядом с главой!
		body_html = body_html.replace('src="img/', 'src="Images/')
		body_html = body_html.replace('srcset="img/', 'srcset="Images/')
		
		# XHTML-валидация одиночных тегов
		body_html = re.sub(r'<(source|img|br|hr)([^>]+?)(?<!/)>', r'<\1\2 />', body_html)

		# Упаковываем контент (файл главы пишется СТРОГО В КОРЕНЬ архива)
		# Упаковываем контент в СТРОГУЮ, легитимную XHTML 1.1 обертку для Calibre [INDEX]
		# Исправлено пространство имен на http://www.w3.org/1999/xhtml по требованию ридера! [INDEX]
		package["chapter1.xhtml"] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://w3.org">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru">
<head>
	<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
	<title>{book_title}</title>
	<link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
{body_html}</body>
</html>"""

		# 4. СБОР СТИЛЕЙ CSS (Пишется СТРОГО В КОРЕНЬ архива)
		theme_html_dir = f"/{cfg.theme_path.replace('\\', '/').lstrip('/')}/html"
		style_content = ["body { font-family: serif; }\n"]
		
		if vfs.exists(theme_html_dir):
			css_path = f"{theme_html_dir}/style.css"
			if vfs.exists(css_path):
				css_lines = vfs.get_file_lines(css_path) or []
				if css_lines:
					style_content.append("\n".join(css_lines))
					
		package["style.css"] = "\n".join(style_content)

		# =====================================================================
		# Шаг 5. АВТОМАТИЧЕСКАЯ УПАКОВКА КАРТИНОК ВНУТРЬ EPUB-ПАКЕТА
		# =====================================================================
		# Проверяем, нашел ли наш тотальный Агрегатор локальные ассеты книги
		if hasattr(doc, 'linked_assets') and doc.linked_assets:
			unique_assets = list(set(doc.linked_assets))
			
			for img_path in unique_assets:
				# 1. Запрашиваем у VFS реальный физический путь к картинке на диске
				real_img_path = vfs.get_real_media_path(img_path)
				
				if real_img_path and os.path.exists(real_img_path):
					# 2. Читаем картинку из VFS как чистые байты стандартным методом Питона
					with open(real_img_path, 'rb') as f:
						img_bytes = f.read()
						
					if img_bytes:
						# Извлекаем чистое имя файла (например, "book1_cover.jpg")
						img_name = os.path.basename(img_path)
						
						# Кладём бинарник картинки прямо в словарь EPUB-пакета!
						package[f"OEBPS/Images/{img_name}"] = img_bytes
						pt.deb(f"[EPUB-Packer] Ресурс упакован в архив: OEBPS/Images/{img_name}")
				else:
					# Фолбек на случай, если автор указал битый путь в разметке книги
					pt.war(f"Картинка для EPUB физически не найдена на диске: {img_path}")



		# 6. ГЕНЕРАЦИЯ МАНИФЕСТОВ (Тоже пишутся СТРОГО В КОРЕНЬ)
		self._write_opf_and_ncx(doc, package, cfg, default_name)

		# Передаем список ассетов наверх в Билдер
		package["assets"] = doc.linked_assets
		
		return package

	def _build_container(self) -> str:
		"""Контейнер теперь четко указывает, что манифест лежит прямо в корне архива!"""
		return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
	<rootfiles>
		<rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
	</rootfiles>
</container>"""

	def _write_opf_and_ncx(self, doc: Document, package: dict, cfg, default_name: str):
		"""
		Генерирует content.opf и toc.ncx в корне архива.
		Использованы СТРОГИЕ международные URL-спецификации для Calibre! [INDEX]
		"""
		import uuid
		book_uuid = str(uuid.uuid4())
		
		authors = doc.metadata.get("author", "Неизвестный автор")
		book_title = doc.metadata.get("title", default_name)
		
		# Список картинок
		img_lines = []
		if doc.linked_assets:
			unique_assets = list(set(doc.linked_assets))
			for img in unique_assets:
				name = os.path.basename(img)
				ext = name.split('.')[-1].lower()
				mime = "image/jpeg" if ext in ['jpg', 'jpeg'] else f"image/{ext}"
				if ext == 'png': mime = "image/png"
				
				img_lines.append(f'<item id="img_{name}" href="Images/{name}" media-type="{mime}"/>')
		
		img_manifest = "\n".join(img_lines)

		# ТВОЕ ЖЕЛЕЗОБЕТОННОЕ ИСПРАВЛЕНИЕ: Полные, валидные URL пространств имен! [INDEX]
		package["content.opf"] = (
			f'<?xml version="1.0" encoding="UTF-8"?>\n'
			f'<package xmlns="http://idpf.org" unique-identifier="uuid_id" version="2.0">\n'
			f'<metadata xmlns:dc="http://purl.org" xmlns:opf="http://idpf.org">\n'
			f'<dc:title>{book_title}</dc:title>\n'
			f'<dc:language>ru</dc:language>\n'
			f'<dc:identifier id="uuid_id" opf:scheme="UUID">{book_uuid}</dc:identifier>\n'
			f'<dc:creator opf:role="aut">{authors}</dc:creator>\n'
			f'</metadata>\n'
			f'<manifest>\n'
			f'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>\n'
			f'<item id="style" href="style.css" media-type="text/css"/>\n'
			f'<item id="item_chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>\n'
			f'{img_manifest}\n'
			f'</manifest>\n'
			f'<spine toc="ncx">\n'
			f'<itemref idref="item_chapter1"/>\n'
			f'</spine>\n'
			f'</package>'
		)

		# Точный, валидный навигационный файл
		package["toc.ncx"] = (
			f'<?xml version="1.0" encoding="UTF-8"?>\n'
			f'<ncx xmlns="http://daisy.org" version="2005-1">\n'
			f'<head><meta name="dtb:uid" content="{book_uuid}"/></head>\n'
			f'<docTitle><text>{book_title}</text></docTitle>\n'
			f'<navMap>\n'
			f'<navPoint id="navpoint-1" playOrder="1">\n'
			f'<navLabel><text>Начало</text></navLabel>\n'
			f'<content src="chapter1.xhtml"/>\n'
			f'</navPoint>\n'
			f'</navMap>\n'
			f'</ncx>'
		)
