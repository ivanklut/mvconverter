"""
===
converter.py
Главный конвейер и точка входа в Ядро Маркван.

На вход получает строки **тела** документа, без титульной информации и отдельно метаданные.
Создаёт объект Document со всеми объектами его составляющими, т.е. абстрактное синтаксическое дерево (Abstract Syntax Tree).
Работает только в памяти.
"""

from rich import print as rprint

from utils import treevisor
from utils import ptlog as pt
from markvan.models import Document
from markvan import parser
from markvan import doc_aggregator


def convert_document(markvan_text: str, meta_data: dict) -> Document:
	"""
	Принимает сырой текст содержания документа одной строкой 
	и словарь глобальных метаданных.
	Проводит данные по конвейеру Ядра и возвращает полностью готовый Document.
	"""
	# === ШАГ 1: ОЧИСТКА ВХОДНОГО МАССИВА СТРОК
	# Уничтожаем текстовые слэши \\n, пойманные в дебаге, и Windows-хвосты \r
	clean_text = markvan_text.replace("\\n", "\n")
	clean_text = clean_text.replace("\r\n", "\n").replace("\r", "\n")
	textlines_list = clean_text.split("\n")

	# === ШАГ 2: ПАРСИНГ КОНТЕНТА
	# Парсеру НЕ нужны метаданные и документ,
	# он возвращает только список объектов AST.
	parsed_nodes = parser.parse_body(lines=textlines_list)

	# === ШАГ 3: РОЖДЕНИЕ ОБЪЕКТА ДОКУМЕНТА
	# Только ТЕПЕРЬ, когда дерево готово, мы создаем глобальный паспорт книги
	doc_obj = Document()
 	# Сохраняем глобальные метаданные (UNO-переменные)	
	doc_obj.metadata = meta_data
	# укладываем дерево нод в корень (body.nodes)
	doc_obj.body.nodes = parsed_nodes


	# # === ШАГ 4: АГРЕГАЦИЯ И АНАЛИТИКА ДАННЫХ 
	# !!! Убрали в def _render_page_tree doc_aggregator.process_document_aggregations(doc_obj)

	# # Собираем оглавление, сноски
	# # Заменяем переменные {{key}} в тексте
	# doc_aggregator.process_document_aggregations(doc_obj)
	
	#rprint(treevisor.build_safe_tree(doc_obj.body))
	# 2. Возвращаем монолитный объект. Внутри него уже лежат:
	# doc_obj.body (дерево секций)
	# doc_obj.linked_assets (список объектов Link для картинок)
	# doc_obj.features (наш свежий список фич для динамических стилей)
	# doc_obj.metadata (UNO-переменные)
	return doc_obj








