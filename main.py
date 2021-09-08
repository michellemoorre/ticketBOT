import logging
import qrcode
import string
import random
import smtplib
from email.message import EmailMessage

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor

class Form(StatesGroup):
	name = State()
	course = State()
	email = State()
	payment = State()



email = 'mikhail.khrshkh@gmail.com'
email2 = 'michaelmar444@gmail.com'
password = 'YiK-mQP-76k-Lc7'

API_TOKEN = '1970152605:AAGvnemP7QDFdESl2TPZCgIBp1LWVdoxs00'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
	await message.answer("покупка \nвведите имя")
	await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
	await state.update_data(name=message.text)
	await message.answer("какой курс?")
	await Form.course.set()

@dp.message_handler(state=Form.course)
async def process_course(message: types.Message, state: FSMContext):
	await state.update_data(course=int(message.text))
	await message.answer("email:")
	await Form.email.set()

@dp.message_handler(state=Form.email)
async def process_email(message: types.Message, state: FSMContext):
	await state.update_data(email=message.text)
#	await Form.payment.set()
#
#@dp.message_handler(state=Form.payment)
#async def send_qr(message: types.Message, state: FSMContext):
	await message.answer("Оплата пройдена")
	ran = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 32))
	img = qrcode.make(ran)
	img.save(ran+".png")
	photo = types.InputFile(ran+".png")
	await bot.send_photo(chat_id=message.chat.id, photo=photo)

	data = await state.get_data()

	msg = EmailMessage()
	msg.set_content('Поздравляем ' + data['name'] + ', Вы успешно купили билет!')

	msg['Subject'] = 'Билеты'
	msg['From'] = email
	msg['To'] = data['email']

	s = smtplib.SMTP('smtp.gmail.com', 587)
	s.starttls()
	s.login(email, password)
	s.send_message(msg)
	s.quit()


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)

