import csv
import os
import FreeCAD as App
import Spreadsheet


def import_csv_to_freecad_spreadsheet(csv_file_path):
  # Получаем текущий документ или создаем новый
  doc = App.activeDocument()
  if not doc:
    doc = App.newDocument('Specification_Project')

  # Создаем объект Spreadsheet
  sheet_name = 'Спецификация_Деталей'
  sheet = doc.getObject(sheet_name)
  if not sheet:
    sheet = doc.addObject('Spreadsheet::Sheet', sheet_name)

  # Вспомогательная функция конвертации индекса колонки в букву (1 -> A, 27 -> AA)
  def col_to_letter(col_idx):
    result = ''
    while col_idx > 0:
      col_idx, remainder = divmod(col_idx - 1, 26)
      result = chr(65 + remainder) + result
    return result

  # Чтение CSV и заполнение ячеек
  if not os.path.exists(csv_file_path):
    App.Console.PrintError(f'Файл не найден: {csv_file_path}\n')
    return

  with open(csv_file_path, mode='r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row_idx, row in enumerate(reader, start=1):
      # Пропускаем полностью пустые строки
      if not any(cell.strip() for cell in row):
        continue

      for col_idx, val in enumerate(row, start=1):
        val_str = val.strip()
        if val_str:
          cell_address = f'{col_to_letter(col_idx)}{row_idx}'
          # Форматируем числовые значения для корректной подстановки
          try:
            # Если значение числовое, сохраняем как число
            num_val = float(val_str.replace(',', '.'))
            sheet.set(cell_address, str(num_val))
          except ValueError:
            # Иначе сохраняем как текст
            sheet.set(cell_address, f"'{val_str}")

  doc.recompute()
  App.Console.PrintMessage(
      f"Таблица успешно импортирована в Spreadsheet '{sheet_name}'!\n"
  )


# Укажите точный путь к файлу на вашем компьютере:
csv_path = r'/media/alex/585082a2-5358-4db4-b760-cb9271302fc81/freecad/puzzle/спека для деталей - Лист1.csv'
import_csv_to_freecad_spreadsheet(csv_path)
