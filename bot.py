import fsm_telebot
from fsm_telebot.storage.memory import MemoryStorage
from telebot import types

from model import Child, Parent, session
from recognition import is_same_person

TOKEN = '973466755:AAHW8JbQ8TTHBUUYcfuC8C4-A1_L2fj1fF8'

storage = MemoryStorage()
bot = fsm_telebot.TeleBot(TOKEN, storage=storage)

choose_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
choose_markup.row('Здати дитину')
choose_markup.row('Забрати дитину')
choose_markup.row('Знайти батьків')
choose_markup.row('Усі діти')
menu_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
menu_markup.row('Меню')


def start():
    bot.polling()


def find_same_person(photo_id, class_obj, child_id=None):
    def url(file_id):
        file = bot.get_file(file_id)
        return f'https://api.telegram.org/file/bot{TOKEN}/{file.file_path}'

    objects = session.query(class_obj)
    if class_obj is Child:
        objects = objects.filter(Child.is_inside)
    elif class_obj is Parent and child_id:
        objects = objects.filter(Parent.child_id == child_id)

    for obj in objects:
        if is_same_person(url(photo_id), url(obj.photo_id)):
            return obj
    return None


@bot.message_handler(func=lambda message: message.text == '/start' or message.text == 'Меню')
def on_start(message):
    bot.send_message(message.chat.id, "Оберіть опцію:",
                     reply_markup=choose_markup)


@bot.message_handler(func=lambda message: message.text == 'Усі діти')
def on_all_children(message):
    children = list(session.query(Child).filter(Child.is_inside))

    if children:
        media_group = [types.InputMediaPhoto(child.photo_id, caption=child.name)
                       for child in children]
        bot.send_media_group(message.chat.id, media_group)
        bot.send_message(message.chat.id, f'В дитячій кімнаті зараз {len(children)} дітей',
                         reply_markup=menu_markup)
    else:
        bot.send_message(message.chat.id, 'В ігровій кімнаті зараз немає дітей',
                         reply_markup=choose_markup)


@bot.message_handler(func=lambda message: message.text == 'Знайти батьків')
def on_get_parent(message):
    bot.send_message(message.chat.id, 'Надішліть фото дитини')
    bot.set_state('expect_child_photo_get_parent', message.chat.id)


@bot.message_handler(state='expect_child_photo_get_parent',
                     content_types=['photo'])
def on_child_photo_get_parent(message):
    bot.send_chat_action(message.chat.id, 'typing')

    photo_id = message.photo[-1].file_id
    child = find_same_person(photo_id, Child)

    if not child:
        bot.send_message(message.chat.id, 'Такої дитини немає в ігровій кімнаті',
                         reply_markup=choose_markup)
    else:
        parents = session.query(Parent).filter(Parent.child_id == child.id)
        media_group = [types.InputMediaPhoto(parent.photo_id,)
                       for parent in parents]
        bot.send_media_group(message.chat.id, media_group)
        bot.send_message(message.chat.id, f'Ім`я дитини: {child.name}. Її батьки:',
                         reply_markup=choose_markup)

    bot.set_state(None, message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Здати дитину')
def on_put_child(message):
    bot.send_message(message.chat.id, 'Як звати вашу дитину?')
    bot.set_state('expect_child_name_begin', message.chat.id)


@bot.message_handler(state='expect_child_name_begin')
def on_child_name_begin(message):
    bot.set_data({'child_name': message.text}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото дитини')
    bot.set_state('expect_child_photo_begin', message.chat.id)


@bot.message_handler(state='expect_child_photo_begin',
                     content_types=['photo'])
def on_child_photo_begin(message):
    photo_id = message.photo[-1].file_id

    bot.update_data({'child_photo_id': photo_id}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото опікуна')
    bot.set_state('expect_first_parent_photo_begin', message.chat.id)


@bot.message_handler(state='expect_first_parent_photo_begin',
                     content_types=['photo'])
def on_first_parent_photo_begin(message):
    photo_id = message.photo[-1].file_id

    bot.update_data({'parents': [photo_id]}, message.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.row('Лише один опікун')
    bot.send_message(message.chat.id,
                     'Якщо вас двоє батьків, то надішліть фото іншого опікуна',
                     reply_markup=markup)
    bot.set_state('expect_second_parent_photo_begin', message.chat.id)


def leave_child(chat_id):
    data = storage.get_data(chat_id)

    child = Child(data['child_name'], data['child_photo_id'])
    session.add(child)
    session.flush()
    session.refresh(child)

    for parent_photo_id in data['parents']:
        parent = Parent(parent_photo_id, child.id)
        session.add(parent)
    session.commit()

    bot.send_message(chat_id, 'Вдалого відпочинку. Щоб забрати дитину'
                              '- оберіть відповідну опцію',
                     reply_markup=choose_markup)
    bot.set_state(None, chat_id)
    bot.reset_data(chat_id)


@bot.message_handler(state='expect_second_parent_photo_begin',
                     func=lambda message: message.text == 'Лише один опікун')
def on_only_one_parent_begin(message):
    leave_child(message.chat.id)


@bot.message_handler(state='expect_second_parent_photo_begin',
                     content_types=['photo'])
def on_second_parent_photo_begin(message):
    photo_id = message.photo[-1].file_id

    data = storage.get_data(message.chat.id)
    data['parents'].append(photo_id)
    bot.update_data(data, message.chat.id)

    leave_child(message.chat.id)


@bot.message_handler(func=lambda message: message.text == 'Забрати дитину')
def on_get_child(message):
    bot.send_message(message.chat.id,
                     'Надішліть фото дитини, яку ви забираєте')
    bot.set_state('expect_child_photo_end', message.chat.id)


@bot.message_handler(state='expect_child_photo_end', content_types=['photo'])
def on_child_photo_end(message):
    photo_id = message.photo[-1].file_id

    bot.set_data({'child_photo_id': photo_id}, message.chat.id)

    bot.send_message(message.chat.id, 'Надішліть фото опікуна, який забирає')
    bot.set_state('expect_parent_photo_end', message.chat.id)


@bot.message_handler(state='expect_parent_photo_end', content_types=['photo'])
def on_parent_photo_end(message):
    bot.send_message(message.chat.id, 'Зачекайте, триває обробка')
    bot.send_chat_action(message.chat.id, 'typing')

    parent_photo_id = message.photo[-1].file_id
    child_photo_id = storage.get_data(message.chat.id)['child_photo_id']

    child = find_same_person(child_photo_id, Child)
    if not child:
        bot.send_message(message.chat.id, 'Такої дитини у нас немає',
                         reply_markup=choose_markup)
    else:
        bot.send_media_group(message.chat.id, [
            types.InputMediaPhoto(child.photo_id),
            types.InputMediaPhoto(child_photo_id)
        ])
        bot.send_message(message.chat.id, 'Дитина до/після')
        bot.send_chat_action(message.chat.id, 'typing')

        parent = find_same_person(parent_photo_id, Parent, child.id)
        if parent:
            bot.send_media_group(message.chat.id, [
                types.InputMediaPhoto(parent.photo_id),
                types.InputMediaPhoto(parent_photo_id)
            ])
            bot.send_message(message.chat.id, 'Опікун до/після')

            bot.send_message(message.chat.id,
                             'Ми вас розпізнали. Можете забрати ваше дитя',
                             reply_markup=menu_markup)

            child.is_inside = False
            session.commit()
        else:
            bot.send_message(message.chat.id,
                             'ТРИВОГА! Несанкціонована спроба забрати дитину',
                             reply_markup=choose_markup)

        bot.set_state(None, message.chat.id)
        bot.reset_data(message.chat.id)
