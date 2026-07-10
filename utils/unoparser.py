def parse_uno_to_dict(uno_text: str) -> dict:
	"""
	Примитивный парсер формата UNO.
	Превращает текст настроек или метаданных в чистый словарь Python.
	Поддерживает вложенность через точку (user.name).
	"""
	data = {}
	if not uno_text.strip():
		return data

	# Разбиваем текст на строки
	lines = uno_text.splitlines()

	for line in lines:
		clean_line = line.strip()
		
		# Пропускаем пустые строки и строковые комментарии
		if not clean_line or clean_line.startswith('//') or clean_line.startswith('#'):
			continue

		# Отрезаем инлайновые комментарии в конце строки
		if '//' in clean_line:
			clean_line = clean_line.split('//', 1)[0].strip()
		if '#' in clean_line:
			clean_line = clean_line.split('#', 1)[0].strip()

		# Снова проверяем, не осталась ли строка пустой после удаления комментариев
		if not clean_line or ':' not in clean_line:
			continue

		# Разделяем по первому двоеточию
		key, val = [p.strip() for p in clean_line.split(':', 1)]
		
		# Очищаем ключ и значение от внешних кавычек, если они есть
		if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
			key = key[1:-1].strip()
		if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
			val = val[1:-1].strip()

		# Конвертируем текстовые параметры в реальные Булевы значения
		if val.lower() in ['true', 'yes', 'on']: 
			val = True
		elif val.lower() in ['false', 'no', 'off']: 
			val = False
		elif val.isdigit():
			val = int(val)

		# Обработка иерархических ключей (например, user.name -> data['user']['name'])
		if '.' in key:
			parts = key.split('.')
			current_level = data
			# Идем по цепочке вложенности, кроме последнего элемента
			for part in parts[:-1]:
				if part not in current_level or not isinstance(current_level[part], dict):
					current_level[part] = {}
				current_level = current_level[part]
			# Записываем значение в самый глубокий уровень
			current_level[parts[-1]] = val
		else:
			data[key] = val

	return data
