from rich.tree import Tree
from rich import print as rprint
from rich.markup import escape  # Важно: защищает от скобок в тексте документа

def build_safe_tree(obj, name_or_key="", tree_node=None, visited=None):
	"""Абсолютно безопасный обход дерева объектов с защитой от разметки rich."""
	if visited is None:
		visited = set()

	# Сразу экранируем ключ/имя поля, чтобы скобки в коде ничего не сломали
	clean_key = escape(str(name_or_key))
	
	# Формируем префикс в зависимости от того, индекс это или имя поля
	if clean_key:
		if clean_key.startswith("[") and clean_key.endswith("]"):
			### Индекс массива 
			prefix = f"[color(248)]{clean_key}[/color(248)] "
		else:
		   
			### Атрибут
			prefix = f"[color(109)]{clean_key}:[/color(109)] "
	else:
		prefix = ""


	# 1. Защита от родительских полей 
	if clean_key.lower() in ['parent', 'owner', 'root_doc', 'document']:
		if tree_node is not None:
			tree_node.add(f"{prefix}[dim]<Ссылка на родителя скрыта>[/dim]")
		return tree_node

	obj_id = id(obj)

	# 2. Формируем имя класса
	class_name = obj.__class__.__name__
	if class_name in ['dict', 'list', 'str', 'int', 'float', 'bool', 'NoneType']:
		### Тип атрибута
		display_name = f"[color(248)]{class_name}[/color(248)]"
	else:
		### Название объекта
		display_name = f"[bold color(107)]{class_name}[/bold color(107)]"
		
	# Безопасное извлечение и экранирование текста документа
	details = ""
	if class_name == 'str':
		safe_str = escape(obj[:30] + '...' if len(obj) > 30 else obj)
		### Текст строки
		details = f" [color(108)]'{safe_str}'[/color(108)]"
	elif hasattr(obj, 'text') and isinstance(getattr(obj, 'text'), str):
		safe_text = escape(getattr(obj, 'text')[:20])
		#details = f" [green]'{safe_text}...'[/green]"

	# 3. Проверка на циклическую ссылку
	is_complex = hasattr(obj, '__dict__') or isinstance(obj, (dict, list, tuple))
	
	if is_complex and obj_id in visited:
		if tree_node is not None:
			tree_node.add(f"{prefix}{display_name} [red](ЦЕНТРАЛЬНЫЙ/ПОВТОРНЫЙ ОБЪЕКТ - ЦИКЛ ПРЕКРАЩЕН)[/red]")
		return tree_node

	if is_complex:
		visited.add(obj_id)

	node_label = f"{prefix}{display_name}{details}"
	if tree_node is None:
		tree_node = Tree(node_label)
	else:
		tree_node = tree_node.add(node_label)

	# 4. РЕКУРСИВНЫЙ ОБХОД
	try:
		if isinstance(obj, dict):
			for key, value in obj.items():
				build_safe_tree(value, name_or_key=key, tree_node=tree_node, visited=visited)
				
		elif isinstance(obj, (list, tuple)):
			for idx, item in enumerate(obj):
				build_safe_tree(item, name_or_key=f"[{idx}]", tree_node=tree_node, visited=visited)
				
		elif hasattr(obj, '__dict__'):
			for attr_name, attr_value in vars(obj).items():
				if attr_name.startswith('__'):
					continue
				build_safe_tree(attr_value, name_or_key=attr_name, tree_node=tree_node, visited=visited)
	except Exception as e:
		tree_node.add(f"[red]Ошибка обхода: {escape(str(e))}[/red]")

	if is_complex:
		visited.remove(obj_id)

	return tree_node

# --- ЗАПУСК ДЕБАГА ---
# visual_tree = build_safe_tree(your_document_object)
# rprint(visual_tree)
