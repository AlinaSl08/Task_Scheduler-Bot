import asyncio
import logging
from idlelib.window import add_windows_to_menu #я это не добавляла, оно само

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


bot = Bot(token="8195780455:AAES5G6RowsVUq6tCkhdEpmKiBCXORNdVq0") #API
dp = Dispatcher(storage=MemoryStorage()) #хранит состояние пользователя(на каком шаге находится)

logging.basicConfig(level=logging.INFO) #уровень логирования

main_router = Router()
dp.include_router(main_router) #добавляет роутер в поле зрения(в диспетчер)

tasks = []



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
    await call.message.delete()

    await state.update_data()  # создаем хранилище, хранит шаг и файл
    bot_msg = await call.message.answer("Напишите название задачи:") #у call обратиться к сообщению и записали туда текст
    await call.answer() #а тут отпрваляем измененное сообщение обратно
    await state.update_data(last_msg_id=bot_msg.message_id) #сохраняем айди сообщения
    await state.set_state(AddTask.name) #задает начало цепочки(откуда стартовать)

#-ФУНКЦИИ КЛАВИАТУРЫ-

# часы 1 часть
@main_router.callback_query(F.data == "next_hour")
async def next_hour(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=get_time_hour_keyboard(2))

# часы 2 часть
@main_router.callback_query(F.data == "prev_hour")
async def prev_hour(call: CallbackQuery):
    await call.message.edit_reply_markup(reply_markup=get_time_hour_keyboard(1))

# минуты
@main_router.callback_query(F.data.startswith ("hour_"))
async def hour_task(call: CallbackQuery):
    hour = call.data.split("_")[1]
    if hour in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        hour = "0" + hour
    await call.message.edit_reply_markup(reply_markup=get_time_minute_keyboard(hour))

# переход от времени к периоду
@main_router.callback_query(F.data.startswith ("time_"))
async def time_task(call: CallbackQuery, state: FSMContext):
    time = call.data.split("_")[1]
    bot_msg = await call.message.answer("По каким дням недели будет повторяться задача?:",
                                   reply_markup=get_period_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(time=time, last_msg_id=bot_msg.message_id)
    # сделаем выбор нескольких дней недели
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

# период повторения(пока 1, надо сделать несколько)
@main_router.callback_query(F.data.startswith ("period_"))
async def period_task(call: CallbackQuery, state: FSMContext):
    period = call.data.split("_")[1]
    bot_msg = await call.message.answer("За сколько напомнить о задаче?:", reply_markup=get_notification_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, call.message)
    await state.update_data(period=period, last_msg_id=bot_msg.message_id)
    await state.set_state(AddTask.notification)
    await call.answer()

#напоминания до задачи есть
@main_router.callback_query(F.data.startswith ("notification_"))
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
    period = data["period"]
    notification = data["notification"]
    # добавляем задачу в список
    tasks.append({"name": name, "date": date, "time": time, "period": period, "notification": notification})
    print(tasks)

    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())

#не напоминать до задачи
@main_router.callback_query(F.data == "no_notification")
async def notification_task(call: CallbackQuery, state: FSMContext):
    notification = "Без напоминаний"
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
    period = data["period"]
    notification = data["notification"]
    # добавляем задачу в список
    tasks.append({"name": name, "date": date, "time": time, "period": period, "notification": notification})
    print(tasks)
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())


#-КЛАВИАТУРЫ-

# клавиатура даты
def get_date_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="<", callback_data="prev_month")
    kb.button(text="Декабрь 2025", callback_data="current_month")
    kb.button(text=">", callback_data="next_month")

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days:
        kb.button(text=day, callback_data=f"day_{day}")

    for i in range(1, 32):
        kb.button(text=str(i), callback_data=f"date_{i}")

    kb.button(text=" ", callback_data="date_")
    kb.button(text=" ", callback_data="date_")
    kb.button(text=" ", callback_data="date_")
    kb.button(text=" ", callback_data="date_")
    kb.adjust(3, 7, 7, 7, 7, 7)
    return kb.as_markup()

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
def get_period_keyboard():
    kb = InlineKeyboardBuilder()
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in days:
        kb.button(text=day, callback_data=f"period_{day}")
    kb.button(text="Не повторять", callback_data=f"no_period")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()

# клавиатура уведомления
def get_notification_keyboard(): # гпт советует использовать CallbackData, но я не поняла
    kb = InlineKeyboardBuilder()
    kb.button(text="10 минут", callback_data="notification_10")
    kb.button(text="30 минут", callback_data="notification_30")
    kb.button(text="1 час", callback_data="notification_60")
    kb.button(text="2 часа", callback_data="notification_120")
    kb.button(text="Не напоминать", callback_data="no_notification")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# -ЦЕПОЧКА ДЕЙСТВИЙ-

# добавляем имя
@main_router.message(AddTask.name)
async def get_name(message: Message, state: FSMContext): #название задачи
    name = message.text #то что получили кладем в переменную
    bot_msg = await message.answer("Напишите дату в формате ДД.ММ.ГГГГ:", reply_markup=get_date_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id") #получаем айди предыдущего сообщения
    await delete_last_message(last_msg_id, message)
    await state.update_data(name=name, last_msg_id=bot_msg.message_id)  # обновить значение(как ключ:значение) и сохранить
    await state.set_state(AddTask.date)


# добавляем дату
@main_router.message(AddTask.date)
async def get_date(message: Message, state: FSMContext):
    date = message.text
    bot_msg = await message.answer("Напишите время выполнения задачи в формате ЧЧ:ММ:", reply_markup=get_time_hour_keyboard())
    data = await state.get_data()
    last_msg_id = data.get("last_msg_id")
    await delete_last_message(last_msg_id, message)
    await state.update_data(date=date, last_msg_id=bot_msg.message_id)
    await state.set_state(AddTask.time) #перенести в клаву


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
@main_router.callback_query(F.data == "delete")
async def delete_task(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("Вы нажали на удалить")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()




#--ВЫВОД СПИСКА--
@main_router.callback_query(F.data == "output")
async def output_task(call: CallbackQuery):
    await call.message.delete()
    if len(tasks) == 0:
        await call.message.answer("🙁 Список пуст!")
        await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await call.answer()
    else:
        tasks_list = ["📌 Список дел:"]
        for task in enumerate(tasks, 1):
            task_text = f'{task[0]}) {task[1]["name"].capitalize()} - {task[1]["date"]["day"]}.{task[1]["date"]["month"]}.{task[1]["date"]["year"]} в {task[1]["time"]["hour"]}:{task[1]["time"]["minute"]} по МСК. Период повторения: {task[1]["period"]}'
            tasks_list.append(task_text)
        full_message = '\n\n'.join(tasks_list)
        await call.message.answer(full_message)
        await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
        await call.answer()



#--ИЗМЕНЕНИЕ--
@main_router.callback_query(F.data == "change")
async def output_task(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("Вы нажали на изменение списка")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()


#--ОЧИЩЕНИЕ--

# клавиатура подтверждения
def confirm_clear_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data="clear_yes")
    kb.button(text="❌ Нет", callback_data="clear_no")
    kb.adjust(2)
    return kb.as_markup()

@main_router.callback_query(F.data == "clear")
async def output_task(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("⚠️ Вы уверены, что хотите удалить ВСЕ задачи?", reply_markup=confirm_clear_keyboard())
    await call.answer()

# очистить список
@main_router.callback_query(F.data == "clear_yes")
async def confirm_clear(call: CallbackQuery):
    await call.message.delete()
    tasks.clear()
    await call.message.answer("🗑️ Все задачи удалены")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()

# очистка списка отменена
@main_router.callback_query(F.data == "clear_no")
async def cancel_clear(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("❎ Очистка отменена")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()


#--НАСТРОЙКИ--
@main_router.callback_query(F.data == "settings")
async def output_task(call: CallbackQuery):
    await call.message.delete()
    await call.message.answer("Вы нажали на настройки")
    await call.message.answer("Выберите действие:", reply_markup=main_menu_keyboard())
    await call.answer()



async def main():
    await set_bot_commands(bot) #задает команды для бота
    await dp.start_polling(bot) #обращается к серверу тг и проверяет на новые сообщения

if __name__ == "__main__": #если запускается из этого файла, то работает, если импортируется, то нет
    asyncio.run(main()) #запуск асинхронности
