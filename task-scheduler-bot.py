import asyncio
import logging

import aiogram
from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand

import calendar
from datetime import datetime


#настроить выбор часового пояса в самом начале использования и потом менять в настройках
#сделать напоминания по времени
#доделать выбор даты
#сделать сохранение в json
#доделать кнопку удаления
#доделать кнопку изменения
#опубликовать бота для постоянной работы
#подключить бд
#сделать статистику по выполненным задачам
#сделать кнопки выполнения задач

bot = Bot(token="8195780455:AAES5G6RowsVUq6tCkhdEpmKiBCXORNdVq0") #API
dp = Dispatcher(storage=MemoryStorage()) #хранит состояние пользователя(на каком шаге находится)

logging.basicConfig(level=logging.INFO) #уровень логирования

main_router = Router()
dp.include_router(main_router) #добавляет роутер в поле зрения(в диспетчер)

tasks = []
days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# функция удаления предыдущего сообщения
async def delete_last_message(last_msg_id: int, message: Message):
    if last_msg_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, #айди текущего смс
                message_id=last_msg_id #айди смс которое хотим удалить
            )
        except aiogram.exceptions.TelegramBadRequest as tbr:
            print("При удалении несуществующего сообщения произошла ошибка!")

#удаление предыдущих сообщений с проверкой
async def safe_delete(message: Message):
    try:
        await message.delete()
    except aiogram.exceptions.TelegramBadRequest:
        pass

#--МЕНЮ--
def main_menu_keyboard():
    kb = InlineKeyboardBuilder() #создаем клавиатуру
    kb.button(text="✔️ Добавить", callback_data="add") #вызов команды, callback_data - данные о вызове
    kb.button(text="🗑️ Удалить", callback_data="delete")
    kb.button(text="💻 Вывести список", callback_data="output")
    kb.button(text="🖊️ Изменить задачу", callback_data="change")
    kb.button(text="❌ Очистить список задач", callback_data="clear")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.adjust(2) #сколько кнопок на строке
    return kb.as_markup() #превращаем в объект клавиатуры


#--СПИСОК КОМАНД--
@main_router.message(Command("start"))
async def start(message = Message): #обозначаем что мы дадим в функцию(какой тип данных)
    await message.answer("Добро пожаловать в чат-бота!", reply_markup=main_menu_keyboard())

@main_router.message(Command("help"))
async def help(message = Message):
    await message.answer("Список доступных команд бота: \n/start\n/help")

# создание подсказать к командам при вводе /
async def set_bot_commands(bot):
    commands = [
        BotCommand(command="start", description="Показать меню"),
        BotCommand(command="help", description="Список команд")
    ]
    await bot.set_my_commands(commands) # отправляем телеграм список команд бота


#--ДОБАВЛЕНИЕ--
class AddTask(StatesGroup):
    name = State()
    date = State()
    time = State()
    period = State()
    notification = State()

@main_router.callback_query(F.data == "add") #обработчик кнопки
async def add_task(call: CallbackQuery, state: FSMContext):
    await safe_delete(call.message)
    await state.update_data()  # создаем хранилище, хранит шаг и файл
    bot_msg = await call.message.answer("Напишите название задачи:") #у call обратиться к сообщению и записали туда текст
    await call.answer() #а тут отправляем измененное сообщение обратно
    await state.update_data(last_msg_id=bot_msg.message_id) #сохраняем айди сообщения
    await state.set_state(AddTask.name) #задает начало цепочки(откуда стартовать)

#-ФУНКЦИИ КЛАВИАТУРЫ-

# часы 1 часть
@main_router.callback_query(F.data == "next_hour")
async def next_hour(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=get_time_hour_keyboard(2))

# часы 2 часть
@main_router.callback_query(F.data == "prev_hour")
async def prev_hour(call: CallbackQuery, state: FSMContext):
    await call.message.edit_reply_markup(reply_markup=get_time_hour_keyboard(1))

# минуты
@main_router.callback_query(F.data.startswith("hour_"))
async def hour_task(call: CallbackQuery, state: FSMContext):
    hour = call.data.split("_")[1]
    if len(hour) == 1:
        hour = "0" + hour
    await call.message.edit_reply_markup(reply_markup=get_time_minute_keyboard(hour))

# переход от времени к периоду
@main_router.callback_query(F.data.startswith("time_"))
async def time_task(call: CallbackQuery, state: FSMContext):
    time = call.data.split("_")[1]
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await safe_delete(call.message)
    #await delete_last_message(last_msg_id, call.message)
    selected = [0, 0, 0, 0, 0, 0, 0]
    bot_msg = await call.message.answer("По каким дням недели будет повторяться задача?:",
                                   reply_markup=get_period_keyboard())

    await state.update_data(time=time, last_msg_id=bot_msg.message_id, selected_days=selected)
    await state.set_state(AddTask.period)
    await call.answer()

# без периода повторения
@main_router.callback_query(F.data == "no_period")
async def period_no(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Задача повторяться не будет!")
    period = 'Без повторений'
    bot_msg = await call.message.answer("За сколько напомнить о задаче?:", reply_markup=get_notification_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(period=period, last_msg_id=bot_msg.message_id)
    await state.set_state(AddTask.notification)
    await call.answer()

# период повторения
@main_router.callback_query(F.data.startswith("period_"))
async def period_task(call: CallbackQuery, state: FSMContext):
    try:
        period = int(call.data.split("_")[1])
        data = await state.get_data()
        selected_days = data.get("selected_days")

        if selected_days[period] == 1:
            await call.answer("Этот день уже выбран 😉")
            return

        selected_days[period] = 1
        await call.message.edit_reply_markup(reply_markup=get_period_keyboard(selected=selected_days, no_period=1))
        await state.update_data(selected_days=selected_days)
    except Exception:
        await call.answer("Произошла ошибка, попробуйте снова")
        await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await call.answer()


@main_router.callback_query(F.data.startswith("continue_get_period"))
async def continue_get_period(call: CallbackQuery, state: FSMContext):
    bot_msg = await call.message.answer("За сколько напомнить о задаче?:", reply_markup=get_notification_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(last_msg_id=bot_msg.message_id)
    await state.set_state(AddTask.notification)
    await call.answer()

#напоминания до задачи есть
@main_router.callback_query(F.data.startswith("notification_"))
async def notification_task(call: CallbackQuery, state: FSMContext):
    notification = int(call.data.split("_")[1])

    bot_msg = await call.message.answer("✔️ Задача успешно добавлена!")
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(notification=notification, last_msg_id=bot_msg.message_id)
    data = await state.get_data()
    name = data["name"]
    date = list(map(int, data["date"].split(".")))
    date = {"day": date[0], "month": date[1], "year": date[2]}
    time = list(map(int, data["time"].split(":")))
    time = {"hour": time[0], "minute": time[1]}
    period = convert_selected_days_to_str(data["selected_days"])
    notification = data["notification"]
    # добавляем задачу в список
    tasks.append({"name": name, "date": date, "time": time, "period": period, "notification": notification})
    print(tasks)

    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())

#не напоминать до задачи
@main_router.callback_query(F.data == "no_notification")
async def notification_task(call: CallbackQuery, state: FSMContext):
    notification = "Без напоминаний"
    bot_msg = await call.message.answer("✅ Задача успешно добавлена!")
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(notification=notification, last_msg_id=bot_msg.message_id)
    data = await state.get_data()
    name = data["name"]
    date = list(map(int, data["date"].split(".")))
    date = {"day": date[0], "month": date[1], "year": date[2]}
    time = list(map(int, data["time"].split(":")))
    time = {"hour": time[0], "minute": time[1]}
    period = data.get("period", "Без повторений")
    notification = data["notification"]
    # добавляем задачу в список
    tasks.append({"name": name, "date": date, "time": time, "period": period, "notification": notification})
    print(tasks)
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())

#-ФУНКЦИИ КЛАВИАТУРЫ ДАТЫ-
#если нажмет пустую стрелочку и если нажмет на месяц и год и если нажимает на день недели
@main_router.callback_query(F.data == "cap")
async def cap(call: CallbackQuery):
    await call.answer("Ошибка, попробуйте снова")

#получаем текущую дату
current_datetime = datetime.now()
current_day = current_datetime.day  # сделать если нажмет меньше этой даты и в том же месяце того же года ошибку
current_month = current_datetime.month
current_year = current_datetime.year

edit_month = current_month

#если нажмет на стрелочку вперед
@main_router.callback_query(F.data == "next_month")
async def next_month(call: CallbackQuery):
    global edit_month
    edit_month = edit_month + 1
    await call.message.edit_reply_markup(reply_markup=get_date_keyboard(current_month=edit_month, cap="<"))


#если нажмет активную стрелку назад
@main_router.callback_query(F.data == "last_month")
async def last_month(call: CallbackQuery):
    global edit_month
    edit_month = edit_month - 1 #тут только на 1 месяц больше берет от сегодняшнего и ошибка
    if edit_month == current_month:
        await call.message.edit_reply_markup(
                              reply_markup=get_date_keyboard(current_month=current_month, cap=" "))
    else:
        await call.message.edit_reply_markup(
                                  reply_markup=get_date_keyboard(current_month=edit_month, cap="<"))



#если нажимает на дату
@main_router.callback_query(F.data.startswith("date_"))
async def choose_date(call: CallbackQuery, state: FSMContext):
    global edit_month
    date_day = int(call.data.split("_")[1])
    date_month = edit_month
    date_year = current_year
    date_str = f"{date_day}.{date_month}.{date_year}"
    await state.update_data(date=date_str)
    await safe_delete(call.message)
    await state.set_state(AddTask.time)
    await call.message.answer("Напишите время выполнения задачи в формате ЧЧ:ММ:", reply_markup=get_time_hour_keyboard())
    edit_month = current_month #сбрасываем дату
    await call.answer()


#-КЛАВИАТУРЫ-

# клавиатура даты
def get_date_keyboard(current_month=current_month, current_year=current_year, cap=" "): #тут сделать надо смену месяцев!
    #делаем клавиатуру
    kb = InlineKeyboardBuilder()
    calendar_for_keyboard = calendar.Calendar().monthdayscalendar(current_year, current_month)
    new_calendar = []
    for days in calendar_for_keyboard:
        for day in days:
            new_calendar.append(day)
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    #шапка календаря
    if cap == " ":
        kb.button(text=f"{cap}", callback_data="cap")
    else:
        kb.button(text=f"{cap}", callback_data="last_month")
    kb.button(text=f"{months[current_month - 1]} {current_year}", callback_data="cap") #если сюда нажмет то уведу
    kb.button(text=">", callback_data="next_month")
    #дни недели
    days_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day_week in days_week:
        kb.button(text=day_week, callback_data=f"cap") #если сюда нажмет то уведу
    #календарь
    for day in new_calendar:
        if day == 0:
            kb.button(text=f" ", callback_data=f"cap")
        else:
            kb.button(text=f"{day}", callback_data=f"date_{day}")
    kb.adjust(3, 7, 7, 7, 7, 7, 7)
    return kb.as_markup()




# получаем нынешний месяц и выводим календарь по номеру месяца в настоящий день, далее используем calendar.Calendar().monthdaycalendar(год, месяц) - получаем список списков на каждую неделю(0=нет дня в месяце)
# current_datetime = datetime.now() ---> current_day = current_datetime.day (и так для месяца и года еще) тут получаем текущий день.мес.год


# клавиатура часов
def get_time_hour_keyboard(page=1):
    kb = InlineKeyboardBuilder()
    if page == 1:
        for i in range(0, 12):
            kb.button(text=str(i), callback_data=f"hour_{i}")
        kb.button(text=">", callback_data=f"next_hour")
    elif page == 2:
        for i in range(12, 24):
            kb.button(text=str(i), callback_data=f"hour_{i}")
        kb.button(text="<", callback_data=f"prev_hour")
    kb.adjust(3, 3, 3, 3, 2)
    return kb.as_markup()

# клавиатура минут
def get_time_minute_keyboard(hour="00"): #тут подставить выбранный час в текст, пример : 15:(текст кнопки)
    kb = InlineKeyboardBuilder()
    for i in range(0, 6):
        kb.button(text=f'{hour}:{i}0', callback_data=f"time_{hour}:{i}0")
        kb.button(text=f'{hour}:{i}5', callback_data=f"time_{hour}:{i}5")
    kb.adjust(4, 4)
    return kb.as_markup()

# клавиатура периода
def get_period_keyboard(selected=[0, 0, 0, 0, 0, 0, 0], no_period=0):
    kb = InlineKeyboardBuilder()
    for i in range(len(selected)):
        smile = ""
        if selected[i] == 1:
            smile = "✅ "
        kb.button(text=f'{smile}{days[i]}', callback_data=f"period_{i}")
    if no_period == 1:
        kb.button(text="Продолжить", callback_data=f"continue_get_period")
    else:
        kb.button(text="Не повторять", callback_data=f"no_period")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()

# клавиатура уведомления
def get_notification_keyboard(): # гпт советует использовать CallbackData, но я не поняла
    kb = InlineKeyboardBuilder()
    kb.button(text="🔔 10 минут", callback_data="notification_10")
    kb.button(text="⏳ 30 минут", callback_data="notification_30")
    kb.button(text="🕐 1 час", callback_data="notification_60")
    kb.button(text="🕒 2 часа", callback_data="notification_120")
    kb.button(text="🚫 Не напоминать", callback_data="no_notification")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# -ЦЕПОЧКА ДЕЙСТВИЙ-

# добавляем имя
@main_router.message(AddTask.name)
async def get_name(message: Message, state: FSMContext): #название задачи
    name = message.text #то что получили кладем в переменную
    bot_msg = await message.answer("Выберите дату выполнения задачи:", reply_markup=get_date_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id") #получаем айди предыдущего сообщения
    await delete_last_message(last_msg_id, message)
    await state.update_data(name=name, last_msg_id=bot_msg.message_id)  # обновить значение(как ключ:значение) и сохранить
    await state.set_state(AddTask.date)

# добавляем дату
@main_router.message(AddTask.date)
async def get_date(message: Message, state: FSMContext):
    bot_msg = await message.answer(
        "Пожалуйста, выберите время с помощью кнопок ниже 👇", reply_markup=get_date_keyboard()
    )
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, message)
    await state.update_data(last_msg_id=bot_msg.message_id)


# добавляем время
@main_router.message(AddTask.time)
async def ignore_time_text(message: Message, state: FSMContext):
    bot_msg = await message.answer(
        "Пожалуйста, выберите время с помощью кнопок ниже 👇", reply_markup=get_time_hour_keyboard()
    )
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, message)
    await state.update_data(last_msg_id=bot_msg.message_id)

# добавляем период
@main_router.message(AddTask.period)
async def ignore_period_text(message: Message, state: FSMContext):
    bot_msg = await message.answer(
        "Пожалуйста, выберите время с помощью кнопок ниже 👇", reply_markup=get_period_keyboard()
    )
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, message)
    await state.update_data(last_msg_id=bot_msg.message_id)

# добавляем уведомление
@main_router.message(AddTask.notification)
async def get_notification(message: Message, state: FSMContext):
    bot_msg = await message.answer(
        "Пожалуйста, выберите время с помощью кнопок ниже 👇", reply_markup=get_notification_keyboard()
    )
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, message)
    await state.update_data(last_msg_id=bot_msg.message_id)



#--УДАЛЕНИЕ--
@main_router.callback_query(F.data == "delete") #делаем клавиатуру состоящую из всех уже сохраненных задач(кол-во кнопок зависит от этого)
async def delete_task(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("Вы нажали на удалить")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()




#--ВЫВОД СПИСКА--
#конвертер периода в дни недели
def convert_selected_days_to_str(selected_days):
    result = []
    for i in range(len(selected_days)):
        if selected_days[i] == 1:
            result.append(days[i])
    return result


@main_router.callback_query(F.data == "output")
async def output_task(call: CallbackQuery):
    await safe_delete(call.message)
    if len(tasks) == 0:
        await call.message.answer("🙁 Список пуст!")
        await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await call.answer()
    else:
        tasks_list = ["📌 Список дел:"]
        for idx, task in enumerate(tasks, 1):
            period = task["period"]
            if isinstance(period, list):
                period_str = ", ".join(period) if period else "Без повторений"
            else:
                period_str = period

            task_text = f'{idx}) {task["name"].capitalize()} - {task["date"]["day"]:02}.{task["date"]["month"]:02}.{task["date"]["year"]} в {task["time"]["hour"]:02}:{task["time"]["minute"]:02}. Период повторения: {period_str}'
            tasks_list.append(task_text)
        full_message = '\n\n'.join(tasks_list)
        await call.message.answer(full_message)
        await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await call.answer()



#--ИЗМЕНЕНИЕ--
@main_router.callback_query(F.data == "change") #делаем клавиатуру состоящую из всех уже сохраненных задач(кол-во кнопок зависит от этого)
async def output_task(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("Вы нажали на изменение списка")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()


#--ОЧИЩЕНИЕ--
@main_router.callback_query(F.data == "clear")
async def output_task(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("⚠️ Вы уверены, что хотите удалить ВСЕ задачи?", reply_markup=confirm_clear_keyboard())
    await call.answer()

#-КЛАВИАТУРА-
# клавиатура подтверждения
def confirm_clear_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data="clear_yes")
    kb.button(text="❌ Нет", callback_data="clear_no")
    kb.adjust(2)
    return kb.as_markup()

#-ФУНКЦИИ КЛАВИАТУРЫ-

# очистить список
@main_router.callback_query(F.data == "clear_yes")
async def confirm_clear(call: CallbackQuery):
    await safe_delete(call.message)
    tasks.clear()
    await call.message.answer("🗑️ Все задачи удалены")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()

# очистка списка отменена
@main_router.callback_query(F.data == "clear_no")
async def cancel_clear(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("❎ Очистка отменена")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()


#--НАСТРОЙКИ--
@main_router.callback_query(F.data == "settings") #сортировка (по дате и времени, по названию), часовой пояс
async def output_task(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("Выберите действие:", reply_markup=settings_menu_keyboard())
    await call.answer()

#-КЛАВИАТУРЫ-

# клавиатура настроек
def settings_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📁 Сортировка", callback_data="sorting")
    kb.button(text="🕰️ Часовой пояс", callback_data="timezone")
    kb.button(text="⬅️ Назад", callback_data="cancel_setting")
    kb.adjust(2, 1)
    return kb.as_markup()

#клавиатура видов сортировки
def sorting_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔤 По названию", callback_data="sort_name")
    kb.button(text="📅 По дате", callback_data="sort_date")
    kb.button(text="⏰ По времени", callback_data="sort_time")
    kb.button(text="⬅️ Назад", callback_data="cancel_setting")
    kb.adjust(2, 2)
    return kb.as_markup()

#клавиатура выбора часового пояса
def time_zone_keyboard():
    kb = InlineKeyboardBuilder()
    for number in ["-2", "-1", "+0", "+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9", "+10"]:
        kb.button(text=f"🌍 UTC{number}", callback_data=f"utc{number}")
    kb.button(text="⬅️ Назад", callback_data="cancel_setting")
    kb.adjust(3, 3, 3, 3, 2)
    return kb.as_markup()

#-ФУНКЦИИ КЛАВИАТУРЫ-

#сортировка по названию
@main_router.callback_query(F.data == "sort_name")
async def sort_name(call: CallbackQuery):
    await safe_delete(call.message)

    #сделать постоянную сортировку

    await call.message.answer("Теперь ваш список сортируется по названию!")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()

#сортировка по дате
@main_router.callback_query(F.data == "sort_date")
async def sort_date(call: CallbackQuery):
    await safe_delete(call.message)

    # сделать постоянную сортировку

    await call.message.answer("Теперь ваш список сортируется по дате!")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()

#сортировка по времени
@main_router.callback_query(F.data == "sort_time")
async def sort_time(call: CallbackQuery):
    await safe_delete(call.message)

    # сделать постоянную сортировку

    await call.message.answer("Теперь ваш список сортируется по времени!")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()

#выбор часового пояса
@main_router.callback_query(F.data.startswith ("utc")) #тут доделать
async def utc_selection(call: CallbackQuery):
    pass

#-СОРТИРОВКА-
@main_router.callback_query(F.data == "sorting")
async def sorting(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("Выберите способ сортировки:", reply_markup=sorting_keyboard())
    await call.answer()

#-ЧАСОВОЙ ПОЯС-
@main_router.callback_query(F.data == "timezone")
async def time_zone(call: CallbackQuery):
    await safe_delete(call.message)
    await call.message.answer("Выберите ваш часовой пояс:", reply_markup=time_zone_keyboard())

#-ВЕРНУТЬСЯ НАЗАД-
@main_router.callback_query(F.data == "cancel_setting")
async def cancel_setting(call: CallbackQuery):
    await safe_delete(call.message)
    await call.answer("Возвращаемся назад...")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()


#--ЗАПУСК БОТА--
async def main():
    await set_bot_commands(bot) #задает команды для бота
    await dp.start_polling(bot) #обращается к серверу тг и проверяет на новые сообщения

if __name__ == "__main__": #если запускается из этого файла, то работает, если импортируется, то нет
    asyncio.run(main()) #запуск асинхронности

