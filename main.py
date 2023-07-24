import requests
from bs4 import BeautifulSoup
import config
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import re

bot = telebot.TeleBot(config.API)


def get_page(url):
    r = requests.get(url)
    return r.text


def collect_postData(url):
    ckm = None
    sid = None
    soup = BeautifulSoup(get_page(url), 'lxml')
    scripts_list = soup.find_all('script')

    for i in scripts_list:
        if "ckm:" in i.text:
            ckm_start = i.text.find('ckm:')
            ckm = i.text[ckm_start + 6:ckm_start + 15]
    sid = soup.find_all('meta')
    for a in sid:
        if a.get('property') == 'og:url':
            sid = a.get('content').split('/')[6]

    dataPost = {
        "action": "requests",
        "ckm": ckm,
        "vca": "cloudflare",
        "y": "2023",
        "uid": "97",
        "sid": sid,
        "last": "0"
    }
    return dataPost

def get_json(url):
    r = requests.post('https://vstup.osvita.ua/api/', data=collect_postData(url) )
    link = r.json()['url']
    return link


def collect_marks(url):
    marks = []
    r_json = requests.get(get_json(url)).json()
    for j in range(0,100000):
        try:
            if r_json['requests'][j][2] != 0:
                ac = r_json['requests'][j][5]
                marks.append(ac)
        except IndexError:
            break
    return marks
def prioritize_marks(url, mark):
    marks_1 = []
    marks_2 = []
    marks_3 = []
    marks_4 = []
    marks_5 = []
    r_json = requests.get(get_json(url)).json()

    for j in range(0,100000):
        try:
            if r_json['requests'][j][2] == 1:
                pr_1 = r_json['requests'][j][5]
                if pr_1 > mark:
                    marks_1.append(pr_1)
            if r_json['requests'][j][2] == 2:
                pr_2 = r_json['requests'][j][5]
                if pr_2 > mark:
                    marks_2.append(pr_2)
            if r_json['requests'][j][2] == 3:
                pr_3 = r_json['requests'][j][5]
                if pr_3 > mark:
                    marks_3.append(pr_3)
            if r_json['requests'][j][2] == 4:
                pr_4 = r_json['requests'][j][5]
                if pr_4 > mark:
                    marks_4.append(pr_4)
            if r_json['requests'][j][2] == 5:
                pr_5 = r_json['requests'][j][5]
                if pr_5 > mark:
                    marks_5.append(pr_5)

        except IndexError:
            break
    return marks_1, marks_2, marks_3, marks_4, marks_5




def collect_volumeData(url):
    data_volumes = []
    dataVolumes = {}
    soup = BeautifulSoup(get_page(url), 'lxml')
    volumeData = soup.find_all('b')
    specialty_name = soup.find('b')
    for i in volumeData:
        if i.text.isdigit():
            data_volumes.append(int(i.text))

    dataVolumes['budgetPlaces'] = data_volumes[2]
    dataVolumes['totalApplicants'] = data_volumes[5]

    return dataVolumes['budgetPlaces'], dataVolumes['totalApplicants'], specialty_name.text


def compare(mark, url):
    higherMarks = []
    for i in collect_marks(url):
        if i > mark:
            higherMarks.append(i)
    return len(higherMarks)+1


@bot.message_handler(commands=['start'])
def start_message(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Вказати посилання на спеціальність: '))
    sent = bot.send_message(message.chat.id, f'Вітаю, {message.from_user.first_name} \nОберіть варіант: ', reply_markup=markup)
    bot.register_next_step_handler(sent, average_score_logic)


@bot.message_handler()
def back_to_menu(message):
    if message.text == 'Назад':
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton('Вказати посилання на спеціальність: '))
        bot.send_message(message.chat.id, 'Оберіть варіант:', reply_markup=markup)
    elif message.text == 'Вказати посилання на спеціальність:':
        average_score_logic(message)


def average_score_logic(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Назад'))
    sent = bot.send_message(message.chat.id, 'Вкажіть ваш середній бал:', reply_markup=markup)
    bot.register_next_step_handler(sent, average_score)


def is_float(s):
    return re.fullmatch(r'^[-+]?\d+(\.\d+)?$', s) is not None


def average_score(message):

    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Назад'))
    if is_float(message.text):
        global mark
        mark = float(message.text)
        sent = bot.send_message(message.chat.id, "Вкажіть посилання на бажану для перегляду спеціальність", reply_markup=markup)
        bot.register_next_step_handler(sent,get_user_link)

    elif is_float(message.text) == False and message.text != 'Назад':
        sent = bot.send_message(message.chat.id, 'Неправильно вказано бал. Спробуйте ще раз.', reply_markup=markup)
        average_score_logic(message)

    else:
        back_to_menu(message)


def get_user_link(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Назад'))
    if "vstup.osvita.ua" in message.text:
        global url
        url = message.text
        main(message)
    elif message.text == "Назад":
        back_to_menu(message)
    else:
        sent = bot.send_message(message.chat.id, "Хибне посилання. Спробуйте ще раз.", reply_markup=markup)
        bot.register_next_step_handler(sent, get_user_link)


def main(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton('Назад'))
    bot.send_message(message.chat.id, f"*{collect_volumeData(url)[2]}*\n\nЗагальна кількість поданих заяв: {collect_volumeData(url)[1]}\n\nЗагальна кількість поданих на бюджет: {len(collect_marks(url))}\n\nКількість бюджетних місць: {collect_volumeData(url)[0]}\n\nКількість поданих заявок по 1 приорітету з вищими балами за ваш: {len(prioritize_marks(url, mark)[0])}\n\nКількість поданих заявок по 2 приорітету з вищими балами за ваш: {len(prioritize_marks(url, mark)[1])}\n\nКількість поданих заявок по 3 приорітету з вищими балами за ваш: {len(prioritize_marks(url, mark)[2])}\n\nКількість поданих заявок по 4 приорітету з вищими балами за ваш: {len(prioritize_marks(url, mark)[3])}\n\nКількість поданих заявок по 5 приорітету з вищими балами за ваш: {len(prioritize_marks(url, mark)[4])}\n\nМоє рейтингове місце: {compare(mark, url)}", parse_mode='Markdown', reply_markup=markup)


if __name__ == "__main__":

    bot.infinity_polling()



