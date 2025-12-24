import asyncio
import logging
from idlelib.window import add_windows_to_menu

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


bot = Bot(token="8195780455:AAES5G6RowsVUq6tCkhdEpmKiBCXORNdVq0") #API
dp = Dispatcher(storage=MemoryStorage()) #хранит состояние пользователя(на каком шаге находится)

logging.basicConfig(level=logging.INFO) #уровень логирования

main_router = Router()
dp.include_router(main_router) #добавляет роутер в поле зрения(в диспетчер)

tasks = []


class AddTask(StatesGroup):
    name = State()
    date = State()
    time = State()
    period = State()
    notification = State()



def main_menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✔️ Добавить", callback_data="add") #вызов команды, callback_data - данные о вызове
    kb.button(text="🗑️ Удалить", callback_data="delete")
    kb.button(text="💻 Вывести список", callback_data="output")
    kb.button(text="🖊️ Изменить задачу", callback_data="change")
    kb.button(text="❌ Очистить список задач", callback_data="clear")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.adjust(2) #сколько кнопок на строке
    return kb.as_markup() #превращаем в объекть клавиатуры




@main_router.message(Command("start"))
async def start(message = Message): #обозначаем что мы дадим в функцию(какой тип данных)
    await message.answer("Добро пожаловать в чат-бота", reply_markup=main_menu_keyboard())

#я сделала
@main_router.message(Command("help"))
async def help(message = Message):
    await message.answer("Список доступных команд бота: \n/start\n/help")



@main_router.callback_query(F.data == "add") #обработчик кнопки
async def add_task(call: CallbackQuery, state: FSMContext):
    await state.update_data()  # создаем хранилище, хранит шаг и файл
    await call.message.answer("Напишите название") #у call обратиться к сообщению и записали туда текст
    await call.answer() #а тут отпрваляем измененное сообщение обратно
    await state.set_state(AddTask.name) #задает начало цепочки(откуда стартовать)



@main_router.message(AddTask.name)
async def get_name(message: Message, state: FSMContext): #название задачи
    name = message.text #то что получили кладем в переменную
    await state.update_data(name=name) #обновить значение(как ключ:значение) и сохранить
    await message.answer("Напишите дату в формате ДД.ММ.ГГГГ:")
    await state.set_state(AddTask.date)

@main_router.message(AddTask.date)
async def get_date(message: Message, state: FSMContext):
    date = message.text
    await state.update_data(date=date)
    await message.answer("Напишите время выполнения задачи в формате ЧЧ:ММ:")
    await state.set_state(AddTask.time)

@main_router.message(AddTask.time)
async def get_time(message: Message, state: FSMContext):
    time = message.text
    await state.update_data(time=time)
    await message.answer("По каким дням недели будет повторяться задача? (пример: 0101101)")
    #сделаем выбор нескольких дней недели
    await state.set_state(AddTask.period)


@main_router.message(AddTask.period)
async def get_period(message: Message, state: FSMContext):
    period = message.text
    await state.update_data(period=period)
    await message.answer("За сколько напомнить о задаче?")
    #сделаем кнопки(несколько)
    await state.set_state(AddTask.notification)


@main_router.message(AddTask.notification)
async def get_notification(message: Message, state: FSMContext):
    notification = message.text
    await state.update_data(notification=notification)

    data = await state.get_data()
    name = data["name"]
    date = list(map(int, data["date"].split(".")))
    date = {"day": date[0], "month" : date[1], "year" : date[2]}
    time = list(map(int, data["time"].split(":")))
    time = {"hour": time[0], "minute": time[1]}
    period = data["period"]
    notification = data["notification"]

    tasks.append({"name": name, "date": date, "time": time, "period": period, "notification": notification})
    await message.answer("Задача успешно добавлена!")
    print(tasks)

@main_router.callback_query(F.data == "delete")
async def delete_task(call: CallbackQuery):
    await call.message.answer("Вы нажали на удалить")
    await call.answer()

#я написала

@main_router.callback_query(F.data == "output")
async def output_task(call: CallbackQuery):
    await call.message.answer("Вы нажали на вывод списка")
    await call.answer()

@main_router.callback_query(F.data == "change")
async def output_task(call: CallbackQuery):
    await call.message.answer("Вы нажали на изменение списка")
    await call.answer()

@main_router.callback_query(F.data == "clear")
async def output_task(call: CallbackQuery):
    await call.message.answer("Вы нажали на очистку списка")
    await call.answer()

@main_router.callback_query(F.data == "settings")
async def output_task(call: CallbackQuery):
    await call.message.answer("Вы нажали на настройки")
    await call.answer()


#здесь будем обрабатывать сообщения

async def main():
    await dp.start_polling(bot) #обращается к серверу тг и проверяет на новые сообщения

if __name__ == "__main__": #если запускается из этого файла, то работает, если импортируется, то нет
    asyncio.run(main()) #запуск асинхронности