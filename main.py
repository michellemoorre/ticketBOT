import os
import logging
import asyncio
import qrcode
import string
import random
import smtplib
import sqlite3
import secrets
from email.message import EmailMessage

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from aiogram.utils.markdown import text, bold, italic, code, pre
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types.message import ContentTypes

class Form(StatesGroup):
	name = State()
	course = State()
	email = State()
	email_check = State()
	send_qr = State()

#google settings
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'keys.json'
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

credentials = service_account.Credentials.from_service_account_file(
		SERVICE_ACCOUNT_FILE, scopes=SCOPES)

service = build('sheets', 'v4', credentials=credentials)

sheet = service.spreadsheets()

#CONSTS
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
API_TOKEN = os.environ.get("API_TOKEN")
PAYMENTS_TOKEN = os.environ.get("PAYMENT_TOKEN")

COST = os.environ.get("COST")

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage, loop=loop)

db = sqlite3.connect('dbdata/tickets.db')
db_cursor = db.cursor()

@dp.message_handler(state='*',commands=['start'])
async def cmd_start(message: types.Message):
	msg = text(bold('Привет'),
			   'Здесь ты можешь купить билет на ___!', 
			   'Instagram и Telegram канал мероприятия: ___', 
			   'Для покупки билетов напиши свое имя в формате ФИО',
			   'Если вдруг ошибся(лась), просто воспользуйся командой /start, чтобы начать с начала!',
			   sep='\n')
	await message.answer(msg, parse_mode=ParseMode.MARKDOWN)
	await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
	await state.update_data(name=message.text)
	await message.answer(text("На каком ты курсе?"), parse_mode=ParseMode.MARKDOWN)
	await Form.course.set()

@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.course)
async def process_gender_invalid(message: types.Message, state: FSMContext):
	return await message.reply("Курс – это число")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.course)
async def process_course(message: types.Message, state: FSMContext):
	await state.update_data(course=int(message.text))
	msg = text(bold('Введи свой учебный email'),
		'Учебная – ___ почта, она оканчивается на ___', 
		sep='\n')
	await message.answer(msg, parse_mode=ParseMode.MARKDOWN)
	await Form.email.set()

@dp.message_handler(lambda message: not message.text.endswith('@edu.hse.ru'), state=Form.email)
async def process_gender_invalid(message: types.Message, state: FSMContext):
	return await message.reply("Проверь еще раз, что почта учебная")

@dp.message_handler(lambda message: message.text.endswith('@edu.hse.ru'), state=Form.email)
async def send_email_code(message: types.Message, state: FSMContext):
	await message.answer(text("Введите проверочный код из письма"), parse_mode=ParseMode.MARKDOWN)
	code = str(random.randint(100000, 999999))
	await state.update_data(email_check=code)
	await state.update_data(email=message.text)
	adresscheck = EmailMessage()
	adresscheck.set_content('Ваш проверочный код: ' + code)
	adresscheck['Subject'] = 'Подтверждение почты'
	adresscheck['From'] = EMAIL_FROM
	adresscheck['To'] = message.text
	s = smtplib.SMTP('smtp.gmail.com', 587)
	s.starttls()
	s.login(EMAIL_FROM, EMAIL_PASSWORD)
	s.send_message(adresscheck)
	s.quit()
	await Form.email_check.set()

@dp.message_handler(state=Form.email_check)
async def check_email_code(message: types.Message, state: FSMContext):
	async with state.proxy() as data:
		email_check = data.get('email_check')
		if email_check == message.text:
			await bot.send_invoice(message.chat.id, title='Ticket',
						   description='В случае возникновения каких-либо затруднений обращаться к ___',
						   provider_token=PAYMENTS_TOKEN,
						   currency='rub',
						   prices=[types.LabeledPrice(label='Билет', amount=COST*100)],
						   is_flexible=False,
						   start_parameter=' ',
						   payload='ticket')
			await Form.send_qr.set()
		else:
			await message.reply("Неверный код, отправляем новое письмо") 
			code = str(random.randint(100000, 999999))
			await state.update_data(email_check=code)
			adresscheck = EmailMessage()
			adresscheck.set_content('Ваш проверочный код: ' + code)
			adresscheck['Subject'] = 'Подтверждение почты'
			adresscheck['From'] = EMAIL_FROM
			adresscheck['To'] = data.get('email')

			s = smtplib.SMTP('smtp.gmail.com', 587)
			s.starttls()
			s.login(EMAIL_FROM, EMAIL_PASSWORD)
			s.send_message(adresscheck)
			s.quit()

@dp.pre_checkout_query_handler(lambda query: True, state=Form.send_qr)
async def checkout(pre_checkout_query: types.PreCheckoutQuery):
	await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
										error_message="")

@dp.message_handler(content_types=ContentTypes.SUCCESSFUL_PAYMENT, state=Form.send_qr)
async def send_qr(message: types.Message, state: FSMContext):
	async with state.proxy() as data:
		user_name = data.get('name')
		user_course = data.get('course')
		user_email = data.get('email')
		personal_key = secrets.token_urlsafe(32)
		img = qrcode.make('http://matfuc.xyz/' + personal_key)
		img.save(personal_key+".png")
		photo = types.InputFile(personal_key+".png")
		#telegram execute
		tele_msg = text(bold('Оплата прошла успешно'),
			'Не теряй QR-код, его нужно будет предъявить на входе.',
			'Его копия отправлена тебе на почту!',
			sep='\n')
		await message.answer(tele_msg, parse_mode=ParseMode.MARKDOWN)
		await bot.send_photo(chat_id=message.chat.id, photo=photo)
		#db execute
		db_cursor.execute(f"INSERT INTO users VALUES ('{personal_key}','{user_name}', {user_course}, '{user_email}')")
		db.commit()
		#google execute
		service.spreadsheets().values().append(
				spreadsheetId=SPREADSHEET_ID,
				range="A:Z",
				body={
					"majorDimension": "ROWS",
					"values": [[personal_key, user_name, user_course]]
				},
				valueInputOption="USER_ENTERED"
			).execute()		
		#email message
		msg = EmailMessage()
		msg.set_content('Поздравляем ' + data.get('name') + ', Вы успешно купили билет!')
		img_data = open(personal_key+".png", 'rb').read()
		msg.add_attachment(img_data, maintype='image', subtype='png')
		msg['Subject'] = 'Билеты'
		msg['From'] = EMAIL_FROM
		msg['To'] = data.get('email')
		s = smtplib.SMTP('smtp.gmail.com', 587)
		s.starttls()
		s.login(EMAIL_FROM, EMAIL_PASSWORD)
		s.send_message(msg)
		s.quit()


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True, loop=loop)

