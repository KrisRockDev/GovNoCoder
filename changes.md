## Основные изменения (v3.6):

1. **Соотношение Панелей:** LEFT_PANEL_EXPAND = 2, RIGHT_PANEL_EXPAND = 8 (20/80).
    
2. **Placeholder Стиль:** Для filter_input, start_prompt_input, end_prompt_input, content_display добавлен hint_style=HINT_STYLE со стилем серого курсива.
    
3. **Перенос Кнопок Select/Deselect:**
    
    - select_all_button и deselect_all_button перенесены в верхнюю панель (ft.Row).
        
    - Изменены на ft.IconButton для единообразия.
        
    - select_buttons_row удален из левой панели.
        
4. **Убраны Подписи у Кнопок:**
    
    - show_content_button и refresh_button изменены с ElevatedButton на IconButton, текст убран.
        
    - Остальные кнопки (copy_button, clear_all_button, кнопки выбора) уже были IconButton.
        
5. **Высота Полей Промптов:** min_lines=3, max_lines=8 для start_prompt_input и end_prompt_input.
    
6. **Индивидуальные Кнопки Очистки:**
    
    - Добавлены clear_start_prompt_button, clear_content_display_button, clear_end_prompt_button (тип IconButton).
        
    - Создана общая функция clear_field(textfield, button) для очистки поля и обновления состояния.
        
    - Создана функция clear_all_fields(e) для общей кнопки, которая вызывает clear_field для всех трех полей.
        
    - Поля ввода и их кнопки очистки обернуты в ft.Row в макете right_panel. Кнопка для content_display размещена под полем справа из-за особенностей растягивания TextField.
        
    - Кнопки очистки полей активируются/деактивируются через on_change соответствующих TextField.
        
7. **Общая Кнопка Очистки:** Кнопка clear_all_button (бывшая clear_content_button) теперь очищает все три поля через clear_all_fields.
    
8. **Горячие Клавиши:**
    
    - Реализован обработчик page.on_keyboard_event = on_keyboard.
        
    - Добавлены комбинации:
        
        - Ctrl+O: Выбрать директорию
            
        - Ctrl+A: Выбрать все
            
        - Esc: Снять выбор
            
        - Enter: Показать/Собрать контент
            
        - Ctrl+R: Обновить дерево
            
        - Ctrl+C: Копировать всё
            
        - Ctrl+X: Очистить все поля
            
    - В tooltip соответствующих кнопок добавлены подсказки с горячими клавишами.
        
    - В обработчике добавлена проверка if not button.disabled перед вызовом действия по горячей клавише.
        
9. **Рефакторинг Состояния Кнопок:**
    
    - Создана единая функция update_button_states(), которая вызывается из разных мест (load_app_state, update_ui_after_selection, clear_ui_on_error, checkbox_changed, toggle_expand, clear_field и т.д.) для централизованного обновления состояния всех кнопок на основе текущего состояния приложения.
        
    - Упрощена логика в scan_and_display_content_sync и других функциях, так как управление состоянием кнопок теперь в update_button_states.
        
10. **Мелкие UI Улучшения:**
    
    - Добавлены ft.VerticalDivider в верхней панели для лучшего визуального разделения групп кнопок.
        
    - Уменьшен spacing в верхней панели и правой панели.
        
    - Добавлен небольшой padding сверху для dir_tree_container.
        
    - Обновлен page.title и версия в логах.
        
    - Увеличены размеры окна по умолчанию.

