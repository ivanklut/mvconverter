# -*- coding: utf-8 -*-
"""
Модуль объектных моделей языка разметки Маркван.

"""
from utils import ptlog as pt

class Document:
	"""Верхний контейнер документа, аккумулирующий контент и метаданные"""
	def __init__(self):
		self.metadata = {}		 	 # Динамический словарь UNO-переменных проекта
		self.title = None			 # Объект Title (Данные из блока ***)
		self.body = Section(level=0) # Нулевая секция — корень всего текстового тела
		self.linked_assets = []		 # Список путей к медиафайлам, требующим копирования
		self.features = {}           # Перечень используемых включений и их классов.
		self.dir_slug = ""           # Относительная папка назначения этого файла при сохранении его в структуре сайта.

# 1. Внутри базового класса Node (в файле моделей) прописываем:
class Node:
	def __init__(self):
		self.node_tag = ""

class Title(Node):
	"""Титульный блок документа (Человекочитаемые метатеги произведения)"""
	def __init__(self, name="", authors=None, year="", genre="", contributors=None, details=None):
		self.name = name
		self.year = year
		self.genre = genre		
		# Безопасная инициализация списка авторов (их может быть несколько)
		self.authors = authors if authors is not None else []		
		# Безопасная инициализация переводчиков/иллюстраторов
		self.contributors = contributors if contributors is not None else []		
		self.node_tag = "title"


# ===
# Элементы тела документа (Nodes)

class Section(Node):
	"""Структурный Раздел — элемент управления иерархическим деревом документа"""
	def __init__(self, level: int):
		super().__init__()
		self.level = level                # Числовой ранг вложенности (0, 1, 2, 3...)
		self.nodes = []                   # Единый хронологический поток всех элементов
		self.parent = None                # Ссылка на родителя для подъема по стеку

class EndSection(Node):
	"""Линейный разделитель (маркер ___). Команда безусловного прерывания контента."""
	pass


class Heading(Node):
	"""Структурный заголовок (открывает новую секцию)"""
	def __init__(self, kind: str, text: str, id_=None, supra: str = ""):
		super().__init__()
		self.kind = kind  				# 'part', 'chapter', 'header'
		self.text = text     # Основное название
		self.supra = supra   # Надзаголовок (Часть 1)
		self.id = id_					# Уникальный идентификатор (#my-id)


class PauseHead(Node):
	"""Логический заголовок-пауза (маркер ~~~) для смены сцены или времени"""
	def __init__(self, text: str = ""):
		super().__init__()
		self.text = text


class Paragraph(Node):
	"""Обычный текстовый абзац прозы"""
	def __init__(self):
		super().__init__()
		self.inlines = []				# Список распарсенных строчных InlineElement
		self.attachments = []			# Список объектов Attachment (ссылки/сноски снизу)


class TermDef(Node):
	"""
	Семантическая пара Термин-Определение.
	Представляет собой одно логическое предложение, разделенное на две части.
	"""
	def __init__(self):
		super().__init__()
		self.term_inlines = []        # Список InlineElement (TextSpan, StyledSpan...) для имени
		self.definition_inlines = []  # Список InlineElement для самого определения


class ContextPair(Node):
	"""Семантическая контекстная пара общего назначения (Монолитный тандем Предикат + Зависимый)"""
	def __init__(self, predicate_node, dependent_node):
		super().__init__()
		self.predicate_node = predicate_node  # Всегда одиночный Paragraph (Ключ/Контекст)
		self.dependent_node = dependent_node  # Paragraph, ListBlock или Inclusion (Значение/Данные)


class ListBlock(Node):
	"""Блок списка, объединяющий элементы одной группы и строку над ним (title)"""
	def __init__(self, kind: str):
		super().__init__()
		self.kind = kind           # 'marked', 'auto_numbered','manual_numbered'
		self.items = []            # Список вложенных объектов ListItem

class ListItem:
	"""Пункты списка (не является самостоятельной Нодой верхнего уровня)"""
	def __init__(self, level: int = 0, manual_number: str = None):
		self.level = level        # Уровень вложенности на основе количества Tab (0, 1, 2...)
		self.manual_number = manual_number # Хранит точный маркер, если он ручной (например, "a)")
		self.inlines = []         # Распарсенные инлайн-элементы (TextSpan, StyledSpan...)
		self.attachments = []	  # Список объектов Attachment (ссылки/сноски снизу)
		self.sub_items = [] 		# Вложенный ListBlock







from utils.makeslug import make_slug
class Link:
	def __init__(self, type: str, address: str, title: str = ""):
		self.type = type
		self.address = address.strip() 
		self.title = title
		self.current_doc_dir = ""
		self.slug_path = ""
		self.is_absolute = None




class FootnoteAttach(Node):
	"""
	Нода описания сноски с диска (|*, |*n, |*#).
	"""
	def __init__(self, id_type: str, text: str):
		super().__init__()
		self.id_type = id_type          # "symbol", "manual", "auto"
		self.res_ftn_id = None          # "*", "1", "вычисленное агрегатором значение" 
		self.text = text#.strip()        # Чистый текст описания сноски


# ===
# Строчные элементы (Inline elements)

class InlineElement:
	"""Базовый абстрактный предок для всех внутристрочных элементов"""
	def __init__(self):
		pass

class FootnoteSpan(InlineElement):
	def __init__(self, id_type: str):
		super().__init__()
		self.id_type = id_type          # "symbol", "manual", "auto"
		self.res_ftn_id = None          # "*", "1", "вычисленное агрегатором значение" 
		# объект FootnoteAttach, чтобы экспортер мог сделать data-tooltip!
		self.footnote_content = None 


class TextSpan(InlineElement):
	"""Обычный голый текст без форматирования"""
	def __init__(self, text: str = ""):
		super().__init__()
		self.text = text

class StyledSpan(InlineElement):
	"""Стилизованный текст с поддержкой вложенных матрешек (bold, italic, sup...) [INDEX]"""
	def __init__(self, style_type: str):
		super().__init__()
		self.style_type = style_type  # 'bold', 'italic', 'small', 'sup', 'sub', 'deleted', 'added' [INDEX]
		self.children = []            # Массив других объектов InlineElement внутри стиля [INDEX]

class VariableSpan(InlineElement):
	"""Ленивая переменная {{key}}, которая заменяется Агрегатором на TextSpan [INDEX]"""
	def __init__(self, key: str):
		super().__init__()
		self.key = key




class LinkSpan(InlineElement):
	"""
	Визуальная гиперссылка, оборачивающая часть контента <[...]> .
	"""
	def __init__(self, link: Link = None):
		super().__init__()
		self.inline_elements = []        # Сюда parse_textline положит распарсенный текст (Объекты: TextSpan, StyledSpan и т.д.)
		self.link = link          # Объект Link (type, address и title)



class InlineIncl(InlineElement):
	"""Изолированные тех-включения &[код]&, %[мат]% со своими CSS-классами [INDEX]"""
	def __init__(self, incl_type: str, text: str, incl_class: str = None):
		super().__init__()
		self.incl_type = incl_type    # 'code', 'math', 'input', 'pre', 'spoiler' [INDEX]
		self.text = text              # Строго СЫРОЙ неизмененный текст внутри включения [INDEX]
		self.incl_class = incl_class  # Опциональный CSS-класс (например, &[print(5)]&rust) [INDEX]


class CommentInline(InlineElement):
	"""Строчный комментарий автора в конце текстовой строки (///, //?, //!)"""
	def __init__(self, kind: str, text: str):
		super().__init__()
		self.kind = kind  # 'note', 'issue', 'todo'
		self.text = text


# ===
# Блочные включения [X … X]

class Inclusion(Node):
	"""Базовый класс для всех блочных включений и сложных контейнеров разметки"""
	def __init__(self, id_=None, incl_class=None, title="", description=""):
		super().__init__()
		self.id = id_
		self.incl_class = incl_class       # Класс типа блока
		self.title = title                 # Название / заголовок блока
		self.description = description     # Описание / подпись под блоком
		self.internal_meta = []            # ЕДИНЫЙ словарь внутренних метаданных из зоны ###
		self.comments = []                 # Комментарии со всех строк: из тела, начала и окончания.


class TextIncl(Inclusion):
	"""Текстовое включение — матрёшка [( ... )]"""
	def __init__(self, **kwargs): 
		super().__init__(**kwargs) 
		self.nodes = []					# Вложенный контент (рекурсивный контейнер)
		self.node_tag = "text"

class CommentIncl(Inclusion):
	"""Скрытый блочный комментарий [/ ... /]"""
	def __init__(self, **kwargs): 
		super().__init__(**kwargs) 
		self.nodes = []
		self.node_tag = "comment"

class PreIncl(Inclusion):
	"""Преформатированный текст [` ... `]"""
	def __init__(self, **kwargs): 
		super().__init__(**kwargs) 
		self.raw_lines = []
		self.node_tag = "pre"


class CodeIncl(Inclusion):
	"""Блок программного кода или музыкальных нот [& ... &]"""
	def __init__(self, **kwargs): 
		super().__init__(**kwargs) 
		self.raw_lines = []
		self.node_tag = "code"


class FormulaIncl(Inclusion):
	"""Блок математических формул [% ... %]"""
	def __init__(self, **kwargs): 
		super().__init__(**kwargs) 
		self.raw_lines = []
		self.node_tag = "math"


class MediaItem:
	"""
	Один физический элемент внутри медиаблока (картинка, трек или видеоролик).
	"""
	def __init__(self, src_path: Link):
		self.src_path = src_path    # Объект Link -- путь к оригиналу файла
		self.action_link: Link | None = None  # Объект Link при клике на картинку (заполнит Агрегатор)
'''
- img2.png — Исходник автора.
- img2~view.webp — Основное отображение в теле документа.
- img2~thumb.webp — Миниатюра для галереи из нескольких штук.
- img2~flscreen.webp — Полноэкранный лайтбокс.
'''

class MediaIncl(Inclusion):
	"""
	Универсальный мультимедийный блок Марквана [[клас_адаптивности класс_медиа ... ]].
	Наследуется от Inclusion, получая id, title, description и incl_class автоматически!
	"""
	def __init__(self, media_class: str = "img", id_: str = "", incl_class: str = "", title: str = "", description: str = ""):
		# Передаем все стандартные паспортные данные наверх в базовый Inclusion
		super().__init__(id_=id_, incl_class=incl_class, title=title, description=description)
		#self.block_caption = ""         # Резерв подписи
		self.items = []                 # Список объектов MediaItem (заполнит Агрегатор)
		self.attachments = []           # Локальный мешок для LinkAttach (|>>) с диска
		self.node_tag = "media"


	
class TableIncl(Inclusion):
	"""Информационная таблица [| ... |]"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs) # Наследуем все атрибуты паспорта включения [INDEX]
		
		# Уникальные внутренние зоны таблицы W3C
		self.thead_rows = []  # Массив объектов TableRow (шапка)
		self.tbody_rows = []  # Массив объектов TableRow (тело)
		self.tfoot_rows = []  # Массив объектов TableRow (подвал)
		self.node_tag = "table"

class TableRow:
	"""Строка таблицы (технический контейнер ячеек)"""
	def __init__(self):
		self.cells = []       # Массив объектов TableCell


class TableCell:
	"""Ячейка таблицы с поддержкой богатого текста и геометрии слияния"""
	def __init__(self, text: str = "", css_class: str = "basic"):
		self.text = text      # Сырой текст (для совместимости)
		self.css_class = css_class  # 'basic', 'total', 'attent', 'number' [INDEX]
		self.colspan = 1
		self.rowspan = 1
		self.is_phantom = False     # Наш флаг 'zero' для поглощенных ячеек
		self.inlines = []     # Распарсенный инлайн-парсером богатый текст! [INDEX]


class GroupingIncl(Inclusion):
	"""Дизайнерский группирующий контейнер (сетки, колонки) [. ... .]"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.nodes = []					# Вложенный контент (рекурсивный контейнер)
		self.node_tag = "group"

class GroupSpacer(Node):
	"""Маркер пустой ячейки .[]."""
	def __init__(self, raw_marker: str = ".[].", **kwargs):
		super().__init__(**kwargs)
		self.raw_marker = raw_marker
		self.node_tag = "gspacer"



class SpoilerIncl(Inclusion):
	"""Скрывающий интерактивный спойлер [_ ... _]"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.nodes = []					# Вложенный контент (рекурсивный контейнер)
		self.is_movable = False			# Флаг для Агрегатора ответов/аппендиксов
		self.node_tag = "spoiler"

class InputIncl(Inclusion):
	"""Блок интерактивного ввода данных (textarea) [$ ... $]"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.node_tag = "input"


# ===
# КЛАССЫ РЕЗУЛЬТАТОВ АГРЕГАЦИИ И ДИНАМИЧЕСКИХ ВСТРАИВАНИЙ 

class Embed(Inclusion):
	"""
	Базовый класс для ДИНАМИЧЕСКИХ встраиваний и блоков Агрегации ({§).
	Наследует всю логику атрибутов и метаданных ###, но служит сигналом 
	для Агрегатора и Экспортера: "Внимание, этот блок наполняется динамически!"
	"""
	def __init__(self, id_=None, incl_class=None, title="", description=""):
		super().__init__(id_=id_, incl_class=incl_class, title=title, description=description)

# --- Ветка динамических встраиваний {{ и Агрегации {§ (Наследуют от Embed!) ---
class TableOfContents(Embed):
	"""Сгенерированное агрегатором оглавление документа/книги {§toc}"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.items = []                  # Список ссылок на Heading, собранный Агрегатором
		self.node_tag = "toc"

class GlossaryBlock(Embed):
	"""Сгенерированный агрегатором список терминов {§glossary}"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.collected_terms = []        # Список объектов TermDef
		self.node_tag = "glossary"

class FootnotesCollectionBlock(Embed):
	"""Место сбора агрегатором примечаний {§footnotes}"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.collected_attachments = []  # Список сносок Attachment
		self.node_tag = "ftncollect"



class SpoilerCollectionBlock(Embed):
	"""Место сбора агрегатором спойлеров(ответов) {§spoiler … §}"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)		
		self.collected_nodes = []		 # Сюда Агрегатор переместит вырезанные спойлеры
		self.node_tag = "spoilercollect"


# ---

# На преобработке всё делаем
# class ExternalImportNode(Embed):
# 	"""Встраивание ноды из текущего или внешнего файла  {{ … }}"""
# 	def __init__(self, **kwargs):
# 		super().__init__(**kwargs)	
# 		self.path = ""		# Путь к внешнему файлу
# 		self.target_id = ""		# Конкретный ID ноды (если указан через #)
# 		# Режим: 'all', 'body' -это класс включения
# 		# all-headstruct body-headstruct -- перерасчитываются заголовки относительно места вставки.


# Поскольку инъекция кода {& ... &} хранит внутри себя строки, которые автор физически написал своими руками на этапе создания файла, семантически это Статический контейнер (Inclusion), а не динамический Embed
class RawCodeBlock(Inclusion):
	"""Прямая инъекция «сырого» технического кода без разметки {& … &} [INDEX]"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)	
		self.raw_lines = []              # Массив строк неизмененного кода (HTML/SVG/JS) [INDEX]
		self.node_tag = "rawcode"