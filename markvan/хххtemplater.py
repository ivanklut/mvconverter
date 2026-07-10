def generate_menu(global_menu_data: list) -> str:
	"""Заглушка генератора меню. Возвращает пустую строку."""
	return "<!-- Глобальное меню навигации -->"

# def render_page(template_html: str, body: str, meta, base_path: str) -> str:
# 	"""
# 	Шаблонизатор-утилита. 
# 	Просто склеивает подготовленный шаблон с контентом страницы.
# 	"""
# 	page_html = template_html.replace("{{content}}", body)
# 	page_html = page_html.replace("{{base_path}}", base_path)
# 	return page_html

def render_page(body_html: str, meta: dict, theme_path: str) -> str:
	# Ищет template.html строго внутри папки theme_path и склеивает с телом книги
	pass