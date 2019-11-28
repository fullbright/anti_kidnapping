import fsm_telebot
from fsm_telebot.storage.memory import MemoryStorage
from telebot import types

from model import Child, Parent, session
import recognition

TOKEN = '973466755:AAHW8JbQ8TTHBUUYcfuC8C4-A1_L2fj1fF8'

storage = MemoryStorage()
bot = fsm_telebot.TeleBot(TOKEN, storage=storage)

empty_markup = types.ReplyKeyboardRemove(selective=False)
choose_markup = types.ReplyKeyboardMarkup()
choose_markup.row('Здати дитину')
choose_markup.row('Забрати дитину')


def start():
    bot.polling()


def get_photo_url_from_message(message):
    file_id = message.photo[-1].file_id
    file = bot.get_file(file_id)
    return f'https://api.telegram.org/file/bot{TOKEN}/{file.file_path}'


@bot.message_handler(commands=['start'])
def on_start(message):
    bot.send_message(message.chat.id, "Оберіть опцію:", reply_markup=choose_markup)


@bot.message_handler(func=lambda message: message.text == 'Здати дитину')
def on_put_child(message):
    bot.send_message(message.chat.id, 'Як звати вашу дитину?', reply_markup=empty_markup)
    bot.set_state('expect_child_name_begin', message.chat.id)


@bot.message_handler(state='expect_child_name_begin')
def on_child_name_begin(message):
    bot.set_data({'child_name': message.text}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото дитини')
    bot.set_state('expect_child_photo_begin', message.chat.id)


@bot.message_handler(state='expect_child_photo_begin', content_types=['photo'])
def on_child_photo_begin(message):
    photo_url = get_photo_url_from_message(message)

    bot.update_data({'child_photo_url': photo_url}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото опікуна')
    bot.set_state('expect_first_parent_photo_begin', message.chat.id)


@bot.message_handler(state='expect_first_parent_photo_begin', content_types=['photo'])
def on_first_parent_photo_begin(message):
    photo_url = get_photo_url_from_message(message)

    bot.update_data({'parents': [photo_url]}, message.chat.id)

    markup = types.ReplyKeyboardMarkup()
    markup.row('Лише один опікун')
    bot.send_message(message.chat.id, 'Якщо вас двоє батьків, то надішліть фото іншого опікуна', reply_markup=markup)
    bot.set_state('expect_second_parent_photo_begin', message.chat.id)


def leave_child(chat_id):
    data = storage.get_data(chat_id)

    child = Child(data['child_name'], data['child_photo_url'])
    session.add(child)
    session.flush()
    session.refresh(child)

    for parent_photo_url in data['parents']:
        parent = Parent(parent_photo_url, child.id)
        session.add(parent)
    session.commit()

    bot.send_message(chat_id, 'Вдалого відпочинку. Щоб забрати дитину - оберіть відповідну опцію', reply_markup=choose_markup)
    bot.set_state(None, chat_id)
    bot.reset_data(chat_id)


@bot.message_handler(state='expect_second_parent_photo_begin', func=lambda message: message.text == 'Лише один опікун')
def on_only_one_parent_begin(message):
    leave_child(message.chat.id)


@bot.message_handler(state='expect_second_parent_photo_begin', content_types=['photo'])
def on_second_parent_photo_begin(message):
    photo_url = get_photo_url_from_message(message)

    data = storage.get_data(message.chat.id)
    data['parents'].append(photo_url)
    bot.update_data(data, message.chat.id)

    leave_child(message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Забрати дитину')
def on_get_child(message):
    bot.send_message(message.chat.id, 'Надішліть фото дитини, яку ви забираєте', reply_markup=empty_markup)
    bot.set_state('expect_child_photo_end', message.chat.id)


@bot.message_handler(state='expect_child_photo_end', content_types=['photo'])
def on_child_photo_end(message):
    photo_url = get_photo_url_from_message(message)

    bot.set_data({'child_photo_url': photo_url}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото опікуна, який забирає')
    bot.set_state('expect_parent_photo_end', message.chat.id)


@bot.message_handler(state='expect_parent_photo_end', content_types=['photo'])
def on_parent_photo_end(message):
    bot.send_message(message.chat.id, 'Зачекайте, триває обробка')

    parent_photo_url = get_photo_url_from_message(message)
    child_photo_url = storage.get_data(message.chat.id)['child_photo_url']

    children = session.query(Child).filter(Child.is_inside)
    valid_children = [child for child in children
                      if recognition.is_the_same_person(child_photo_url, child.photo_url)]

    if not valid_children:
        bot.send_message(message.chat.id, 'Такої дитини у нас немає')
    else:
        child = valid_children[0]
        bot.send_message(message.chat.id, f'Ви хочете забрати дитину з іменем: {child.name}')

        parents = session.query(Parent).filter(Parent.child_id == child.id)
        valid_parents = [parent for parent in parents
                         if recognition.is_the_same_person(parent_photo_url, parent.photo_url)]
        if valid_parents:
            bot.send_message(message.chat.id, 'Дякуємо! Ми вас розпізнали. Можете забрати ваше дитя',
                             reply_markup=choose_markup)
            child.is_inside = False
            session.commit()
        else:
            bot.send_message(message.chat.id, 'ТРИВОГА! Несанкціонована спроба забрати дитину',
                             reply_markup=choose_markup)

        bot.set_state(None, message.chat.id)
        bot.reset_data(message.chat.id)
