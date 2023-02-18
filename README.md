# Telegram Cleaner

Delete all Telegram chat messages and group posts and channel comments.

**RUSSIAN DISCLAIMER**: Telegram не является анонимным и никогда им не был. Сотрудникам спецслужб известны телефонные номера около 30 миллионов пользователей Telegram из России, а равно и паспортные данных их владельцев. До 2020 года по телефону можно было найти любого пользователя. Чекистские подстилки массово скупали симки, вбивали в контакты тысячи случайных номеров, а потом сохраняли в базе связку id и номер телефона. Так собиралась пользовательская база, например, «Глаза Бога». С учетом того, что Роскомнадзор запустил бота для поиска экстремистских комментариев в сети, в т.ч. в Telegram настоятельно советую удалить свои старые аккаунты, предварительно потерев комментарии в группах. Также помните, что Telegram сотрудничает с ФСБ и другими спецслужбами и занимается выдачей террористов. Если сотрудники телеги получат на вас запрос от гэбни, то никто из них не удосужится выяснить, настоящий вы террорист ИГИЛ или это обычный спам запросами на неугодных режиму, они просто передадут ваши ip-адрес и номер телефона.

**WARNING**: before using this utility, you can save all your data using the desktop application: `Settings ` > ` Advanced` > `Export Telegram data`.

Installation:

```bash
# via pip
$ pip install -U telegram-cleaner

# via pipx
$ pipx install telegram-cleaner
```

Usage:

```bash
# see help
$ tg-clean -h

# first save chat usernames and indetifiers
$ tg-clean print_chats > chats.dump.txt 

# delete messages in group chats, comments, posts
$ tg-clean -vvy delete_group_messages

# delete private chats
$ tg-clean -vvy delete_private_chats

# delete all your messages
$ tg-clean

# You cand use you own telegram application
# Add this lines to ~/.bashrc or ~/.zshrc
# Also you can use .env files with zsh dotenv plugin
export TG_API_ID=6
export TG_API_HASH=eb06d4abfb49dc3eeb1aeb98ae0f581e
```
