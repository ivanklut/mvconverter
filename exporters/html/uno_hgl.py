"""
Модуль преобразует UNO text в html.
https://unotext.mudrium.ru/

Разбивает строку на логические элементы и оборачивает каждый в span с соответствующим классом.
Классы элементов:
- ind - indent - отступ показывающий вложенность
- key - key - ключ
- insk - insert key - ключ по которому втавляется значение
- dot - key separator dot - точка разделяющая ключи
- sep - separator - разделитель ключа и значения
- mod - modifier - модификатор
- gap - пробел перед значением или двойной перед комментарием
- vstr - value string - строковое значение
- vnum - value number - числовое и прочее нестроковое значение
- bool - boolean - булево значение
- prf - prefix - признак системы счисления
- unl - underline - подчёркивание
- exp - exponenta - знак экспоненты
- pval - paired value - величина спаренного значение
- unit - единица измерения спаренного значения
- quo - escape quotation mark - экранирующая кавычка
- lit - list item - знак элемента массива
- com - comment - комментарий
- imp - import - импорт файла
- met - metadata - обозначение метаданных
- brk - bracket - скобка
//- cmm - comma запятая разделяющая элементы списка или словаря

Здравствуйте. Немного отвлеку вас. Придумал вариацию на тему  YAML, TOML.
Понадобилось для одного проекта что-то типа конфигурационного файла (скорее описательного), чтобы его смогли заполнять обычные люди. Вы может ещё помните свои ощущения когда впервые встретились со скобками в HTML или JSON, особенно когда есть некая вложенность данных.
Называется *UNO text*. Можно использовать для формального описания каких-либо объектов в качестве миниатюрной базы данных или для передаобмена данными. Пока только основные идеи сформулировал, на практике не успел проработать.
https://unotext.mudrium.ru/
Если будут замечания и предложения, пишите в личку.

///Придумать нотацию как показать структуру функций
def convert_code_to_html (code_text) -> html  // оборачивает кусочки строки в html
	def code_markup(code_lines_list) -> [{klass: value}] // проверяет по первому символу что за класс
		def split_record (line) -> ind, key, ...   // обрабатывает строки с записями
			def split_val_com(line) -> val, com  // разделяет значение и допкомментарий
author:
	name: Klut Ivan
	mail: ivan@klut.ru
"""

def convert_code_to_html (code_text) -> str:
	code_lines_list = code_text #list(code_text.split('\n'))
	# Предварительная разметка
	markup_lines_list = code_markup(code_lines_list) 
	# Получили построчный список со списками элементов в виде кортежа (класс: значение)
	# Обобрачиваем html-тегами
	html = ''
	for line in markup_lines_list:
		if line == []:
			html += '\n'
			continue
		for el in line:
			if el:
				clas, val = el
				html += f'<span class="{clas}">{val}</span>'
		html += '\n'
	html = html[0:-1]
	print(html)
	return html


def code_markup(code_lines_list) -> list:
	"""
	-> [[('key1', 'val1'),('key2', 'val2')], []]
	Определяем по первому символу тип строки, при необходимости отправляем на додешифровку в другие функции.
	"""
	markup_lines_list = []  # список строк, содержащий списки маркированных частей кодовой строки (кортежей)
	flag_multicomment = False
	flag_multistring = False

	for line in code_lines_list:
		temp_line = []
		l_strp = line.strip()  # отбрасываем отступы и табы

		# Пустые строки не теряем
		if l_strp == '':
			markup_lines_list.append([])
			continue

		# Если в предыдущей итерации цикла определили многострочный комментарий.
		if flag_multicomment:
			markup_lines_list.append([('com', line)])
			if l_strp[0:2] == "*/":  # конец многострочного комментария
				flag_multicomment = False
			continue

		# Если в предыдущей итерации цикла определили многострочный текст.
		if flag_multistring:			
			if l_strp == "'":  # конец многострочного комментария				
				markup_lines_list.append([('quo', "'")])
				flag_multistring = False
			else:
				markup_lines_list.append([('vstr', line)])
			continue

		# Проверка по первому непробельному символу строки. Простые случаи обрабатываем сразу.
		match l_strp[0]:
			case '/':
				if l_strp[0:2] == '//':   # проверка на однострочные комментарии
					markup_lines_list.append([('com', line)])
					continue
				elif l_strp[0:2] == '/*':  # проверка на многострочные комментарии
					flag_multicomment = True
					markup_lines_list.append([('com', line)])
					continue
			case '#':  # метаданные
				temp_line.append(('meta', '#'))
				temp_line.append(('gap', ' '))
				temp_line += (scan_record(l_strp[1:]))
				markup_lines_list.append(temp_line)
				continue
			case '@':  # импорты
				if line[0:7] == '@import':
					temp_line.append(('imp', '@import'))
					temp_line.append(('gap', ' '))
					_, value, comment = search_comment(l_strp[7:])
					temp_line.append(('vstr', value)) 
					if comment:
						temp_line.append(('com', comment))
					markup_lines_list.append(temp_line)
				continue
			case "'":  # проверка на многострочные тексты
				if l_strp == "'":
					flag_multistring = True
					markup_lines_list.append([('quo', "'")])
					continue
				else:
					markup_lines_list.append(scan_record(line))
			case '-':  # это значение списка или ключ
				if l_strp == '-':  #если элемент без названия
					markup_lines_list.append([('lit', '-')])
					continue
				else:  # анализируем строку целиком в отдельной функции				
					markup_lines_list.append(scan_record(line))
					continue	
			case '=':  # это значение списка или ключ
				markup_lines_list.append(scan_record(line))
				continue				
			case _:  # это просто ключ-значение (или опечатка)
				markup_lines_list.append(scan_record(line))
	return markup_lines_list


def scan_record (line) -> list:
	""" 
	-> [('key1', 'val1'),('key2', 'val2')]
	Разделяем строку на части: ключ, разделитель, модификатор (и их составляющие).
	"""	
	markup_line = [] # Список элементов виде кортежей
	key_temp = ''
	sep = ''
	mod = ''
	temp = ''
	sumb = ''
	lit = ''
	# Выделяем отступ
	for n, sumb in enumerate(line):
		if sumb == '\t':
			markup_line.append(('ind', '\t'))
		else:
			line = line[n:]
			break

	# Если есть признак значения массива
	if line[0] == '-':
		lit = '-'
		markup_line.append(('lit', lit))
		#markup_line.append(('gap', ' '))
		line = line[1:]
	if line[0] == '=':
		lit = '='
		markup_line.append(('lit', lit))
		#markup_line.append(('gap', ' '))
		line = line[1:]

	# Ищем разделитель
	for n, sumb in enumerate(line):
		match sumb:
			case ':':
				if temp[-4:] == 'http' or temp[-5:] == 'https':
					temp += sumb
					continue
				sep = ':'
				key_temp = temp
				temp = ''
				# отделим признак списка от ключа
				if lit == '-':
					markup_line.append(('gap', ' '))
				for el in key_markup(key_temp):
					markup_line.append(el)
				markup_line.append(('sep', sep))
				line = line[n+1:]
				break
			case '=':
				key_temp = temp
				temp = ''
				sep = '='
				if key_temp:
					for el in key_markup(key_temp):
						markup_line.append(el)
					markup_line.append(('sep', sep))
					line = line[n+1:]
				break
			case _:
				temp += sumb
				continue
	
	# Ищем модификатор
	if sep and len(line) > 0:
		mods = ['+', '*', '&']
		if line[0] in mods:
			markup_line.append(('mod', line[0]))
			mod = line[0]
			line = line[1:]


	# Выделяем значение и комментарий	
	if line:
		quote, full_value, comment = search_comment(line)
		print('quote, full_value, comment', quote, '-', full_value, '-',comment)

		markup_line.append(('gap', ' '))			

		if quote:
			markup_line.append(('quo', quote))

		# Разбираемся со значением
		if sep:
			# Обрабатываем строчное представление списка или объекта, спаренное значение
			for el in value_markup(sep, mod, full_value):
				markup_line.append(el)
		else:
			# Если разделителя не было, значит это значение массива. Прекращаем анализ
			for el in value_markup(lit, mod, full_value):
				markup_line.append(el)
	
		if quote:
			markup_line.append(('quo', quote))

		# Добавляем комментарий
		if comment:
			markup_line.append(('gap', '  '))	
			markup_line.append(('com', comment))
	
	return markup_line


def key_markup(line) -> list:
	""" -> -> [('key1', 'val1'),('key2', 'val2')]
	Проверяем ключ на кавычки и точки
	"""
	line = line.strip()
	if line[0] == '-':
		line = line[1:]
	key_elems = []
	el_temp = ''
	sumb = ''
	
	if line[0] == "'":		
		key_elems.append(('quo', "'"))
		key_elems.append(('key', line[1:-1]))
		key_elems.append(('quo', "'"))
	else:
		for sumb in line:
			if sumb != '.':
				el_temp += sumb
			else:
				key_elems.append(('key', el_temp))
				el_temp = ''
				key_elems.append(('dot', "."))
		key_elems.append(('key', el_temp))
				
	return key_elems


def value_markup(sign_type, modificator, line) -> list:
	""" -> [('key1', 'val1'),('key2', 'val2')]
	Проверяем ключ на кавычки и точки
	"""
	key_elems = []
	line = line.strip()
	if not line:
		return [('vstr', '')]

	# # Сначала проверим не являются ли значения списками или кортежами
	# if line[0] == '{' and line[-1] == '}':
	# 	#! Добавить исключение для модификатора &. task_url:& { base_url}task-{task-number}
	# 	key_elems.append(('brk', '{'))
	# 	ln = line[1:-1].split(',')  #! Если пользователь использует запятую в value, то неправильно разобъёт
	# 	print('ln', ln)
	# 	for l in ln:
	# 		key_elems+= scan_record(l)
	# 		key_elems.append(('cmm', ', '))
	# 	key_elems.pop()
	# 	key_elems.append(('brk', '}'))

	# elif line[0] == '[' and line[-1] == ']':
	# 	key_elems.append(('brk', '['))
	# 	ln = line[1:-1].split(',')  #! Если пользователь использует запятую в value, то неправильно разобъёт
	# 	print('ln', ln)
	# 	for l in ln:
	# 		key_elems+= value_markup(sign_type,l)
	# 		key_elems.append(('cmm', ', '))
	# 	key_elems.pop()
	# 	key_elems.append(('brk', ']'))

	bools = ['true', 'false', 'on', 'off', 'open', 'close', 'yes', 'not']

	if sign_type == '-':
		key_elems.append(('vstr', line))

	elif sign_type == ':':
		temp = ''
		if modificator == '&':  # подсветим ключ, значение которого импортируется
			flag_brackets = False
			for sumb in line:
				match sumb:
					case '{':
						key_elems.append(('vstr', temp))
						temp = ''
						key_elems.append(('brk', '{'))
					case '}':
						key_elems.append(('insk', temp))
						temp = ''
						key_elems.append(('brk', '}'))
						flag_brackets = True
					case _:
						temp += sumb
			# последняя часть вне скобок
			if temp:
				if flag_brackets:
					key_elems.append(('vstr', temp))
				else:
					key_elems.append(('insk', temp))
		else:
			key_elems.append(('vstr', line))	
	
	elif sign_type == '=':
		# проверка недесятичных чисел
		prefix_numb_sys = ['0b', '0o', '0x']		
		pref = line[0:2]
		if pref in prefix_numb_sys:
			key_elems.append(('prf', pref))
			key_elems.append(('vnum', line[2:]))
		# проверка логических значений	
		elif line.lower() in bools:
			key_elems.append(('bool', line))		
		# проверка спаренных значений, подчёркиваний	
		elif line[0] != '(':
			value = ''
			sign_unit = False
			for sumb in line:
				match sumb:
					case '_':
						key_elems.append(('vnum', value))
						key_elems.append(('unl', '_'))
						value = ''
					case 'e':
						key_elems.append(('vnum', value))
						key_elems.append(('exp', 'e'))
						value = ''					
					case 'E':
						key_elems.append(('vnum', value))
						key_elems.append(('exp', 'E'))
						value = ''
					case '-':
						key_elems.append(('vnum', value))
						key_elems.append(('unl', '-'))
						value = ''
					case ':':
						key_elems.append(('vnum', value))
						key_elems.append(('unl', ':'))
						value = ''
					case '.':
						key_elems.append(('vnum', value))
						key_elems.append(('unl', '.'))
						value = ''
					case ' ':
						key_elems.append(('vnum', value))
						key_elems.append(('gap', ' '))	
						sign_unit = True
						value = ''
					case _ :
						value += sumb

			if sign_unit:
				key_elems.append(('unit', value))
			else:
				key_elems.append(('vnum', value))
		else:
			key_elems.append(('vnum', line))



	else:
		print('else:', line)
		key_elems.append(('vstr', line))

		
	return key_elems



def search_comment(pc_line) -> tuple:
	"""
	-> sign_string_value, value, comment
	Разделяем значение записи и комментарий
	"""
	pc_line = pc_line.strip()
	# Определяем наличие кавычек, чтобы не учитывать признак комментария внутри них
	sign_string_value = ''
	first = pc_line[0]
	if first == "'":
		sign_string_value = "'"
	elif first == '"':
		sign_string_value = '"'
	
	temp = ''
	value = ''
	comment = ''
	# Если начинается с кавычки, то ищем закрывающую кавычку
	if sign_string_value: 
		for n, sumb in enumerate(pc_line):
			if sumb == sign_string_value:
				value = temp
				temp = ''
			else:
				temp += sumb
		if len(temp) >= 2 and temp.strip()[0:2] == '//':
				comment = temp

		# обработка оставшейся части или без кавычек
	else:
		for i in range(len(pc_line)-1):
			if pc_line[i:i+2] == '//':
				if i == 0:
					comment = pc_line[i:]
					value = ''
					break
				else:
					if pc_line[i-1] != ':':  # исключим http://example.com
						value = pc_line[:i]
						comment = pc_line[i:]
					break

		# если значение не было найдено ранее (т.к. комментарий не встречался)
		if not comment and not value:  
			value = pc_line
		if comment:
			comment = comment  # отступ в 2 пробела

	return (sign_string_value, value, comment)



if __name__ == '__main__':
	text = '''object.key2= number_value2'''
	a = convert_code_to_html(text)
