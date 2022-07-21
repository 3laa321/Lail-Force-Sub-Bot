import time
import logging
from Config import Config
from pyrogram import Client, filters
from sql_helpers import forceSubscribe_sql as sql
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, UsernameNotOccupied, ChatAdminRequired, PeerIdInvalid

logging.basicConfig(level=logging.INFO)

static_data_filter = filters.create(lambda _, __, query: query.data == "onUnMuteRequest")
@Client.on_callback_query(static_data_filter)
def _onUnMuteRequest(client, cb):
  user_id = cb.from_user.id
  chat_id = cb.message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    channel = chat_db.channel
    chat_member = client.get_chat_member(chat_id, user_id)
    if chat_member.restricted_by:
      if chat_member.restricted_by.id == (client.get_me()).id:
          try:
            client.get_chat_member(channel, user_id)
            client.unban_chat_member(chat_id, user_id)
            if cb.message.reply_to_message.from_user.id == user_id:
              cb.message.delete()
          except UserNotParticipant:
            client.answer_callback_query(cb.id, text="انضم الى القناه و اضغط **الغاء كتمي** .", show_alert=True)
      else:
        client.answer_callback_query(cb.id, text="❗ تم كتم صوتك بواسطة المسؤولين لأسباب أخرى.", show_alert=True)
    else:
      if not client.get_chat_member(chat_id, (client.get_me()).id).status == 'administrator':
        client.send_message(chat_id, f" **المستخدم {cb.from_user.mention} يحاول إلغاء كتم الصوت بنفسه ولكن لا يمكنني إلغاء كتمه لأنني لست مشرفًا في هذه الدردشة ، أضفني كمسؤول مرة أخرى. **\n__# ترك هذه الدردشة...__")
        client.leave_chat(chat_id)
      else:
        client.answer_callback_query(cb.id, text="❗ تحذير: لا تنقر فوق الزر إذا كنت تستطيع التحدث بحرية.", show_alert=True)



@Client.on_message(filters.text & ~filters.private & ~filters.edited, group=1)
def _check_member(client, message):
  chat_id = message.chat.id
  chat_db = sql.fs_settings(chat_id)
  if chat_db:
    user_id = message.from_user.id
    if not client.get_chat_member(chat_id, user_id).status in ("administrator", "creator") and not user_id in Config.SUDO_USERS:
      channel = chat_db.channel
      try:
        client.get_chat_member(channel, user_id)
      except UserNotParticipant:
        try:
          sent_message = message.reply_text(
              "{},  عذرا انت قر مشترك فى [قناه](https://t.me/{}) حتي الان. من فضلك [انضم](https://t.me/{}) ثم **اضغط الزر في الاسفل** لالغاء الكتم عن نفسك.".format(message.from_user.mention, channel, channel),
              disable_web_page_preview=True,
              reply_markup=InlineKeyboardMarkup(
                  [[InlineKeyboardButton("انضم الى القناه", url=f"https://t.me/{channel}")],
                   [InlineKeyboardButton("الغاء كتمي", callback_data="onUnMuteRequest")]]
              )
          )
          client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
        except ChatAdminRequired:
          sent_message.edit("❗ ** لست مشرفًا هنا. ** \ n__ اجعلني مشرفًا بإذن حظر المستخدم وأضفني مرة أخرى. \ n # ترك هذه الدردشة ...__")
          client.leave_chat(chat_id)
      except ChatAdminRequired:
        client.send_message(chat_id, text=f"❗ **لست ادمن في قناه  @{channel}**\n__اضفني ادمن في القناه و جرب مره اخرى.\n#ترك هذه المحادثه...__")
        client.leave_chat(chat_id)


@Client.on_message(filters.command(["forcesubscribe", "fsub"]) & ~filters.private)
def config(client, message):
  user = client.get_chat_member(message.chat.id, message.from_user.id)
  if user.status is "creator" or user.user.id in Config.SUDO_USERS:
    chat_id = message.chat.id
    if len(message.command) > 1:
      input_str = message.command[1]
      input_str = input_str.replace("@", "")
      if input_str.lower() in ("off", "no", "disable"):
        sql.disapprove(chat_id)
        message.reply_text("❌ ** تم تعطيل فرض الاشتراك بنجاح. **")
      elif input_str.lower() in ('clear'):
        sent_message = message.reply_text('** إلغاء كتم صوت جميع الأعضاء الذين تم كتم صوتهم بواسطتي ... **')
        try:
          for chat_member in client.get_chat_members(message.chat.id, filter="restricted"):
            if chat_member.restricted_by.id == (client.get_me()).id:
                client.unban_chat_member(chat_id, chat_member.user.id)
                time.sleep(1)
          sent_message.edit('✅ ** تم إلغاء كتم صوت جميع الأعضاء الذين قمت بكتم صوتهم. **')
        except ChatAdminRequired:
          sent_message.edit('❗ ** أنا لست مسؤولاً في هذه الدردشة. ** \ n__ لا يمكنني إلغاء كتم صوت الأعضاء لأنني لست مسؤولاً في هذه الدردشة جعلني مسؤولاً بإذن حظر المستخدم .__')
      else:
        try:
          client.get_chat_member(input_str, "me")
          sql.add_channel(chat_id, input_str)
          message.reply_text(f"✅ ** تم تفعيل فرض الاشتراك ** \ n__ تم تفعيل اشتراك القوة ، يجب على جميع أعضاء المجموعة الاشتراك في هذه [القناة](https://t.me/{input_str}) من أجل إرسال رسائل في هذه المجموعة .__", disable_web_page_preview=True)
        except UserNotParticipant:
          message.reply_text(f"❗ ** لست مسؤولاً في القناة ** \ n__ أنا لست مسؤولاً في [القناة](https://t.me/{input_str}).أضفني كمسؤول من أجل تمكين الاشتراك الاجبارى .__", disable_web_page_preview=True)
        except (UsernameNotOccupied, PeerIdInvalid):
          message.reply_text(f"❗ ** اسم مستخدم قناة غير صالح. **")
        except Exception as err:
          message.reply_text(f"❗ ** خطأ: ** ```{err}```")
    else:
      if sql.fs_settings(chat_id):
        message.reply_text(f"✅ ** تم تفعيل فرض الاشتراك في هذه الدردشة. ** \ n__ لهذه [القناة](https://t.me/{sql.fs_settings(chat_id).channel})__", disable_web_page_preview=True)
      else:
        message.reply_text("❌ ** تم تعطيل فرض الاشتراك في هذه الدردشة. **")
  else:
      message.reply_text("❗ ** مطلوب منشئ المجموعة ** \ n__ يجب أن تكون منشئ المجموعة للقيام بذلك .__")
