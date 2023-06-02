from telebot.util import quick_markup

search_manga_acc_inline = quick_markup({'←': {'callback_data': 'prev_manga_acc'},
                                        '→': {'callback_data': 'next_manga_acc'},
                                        '✅': {'callback_data': 'add_manga_acc'},
                                        '❌': {'callback_data': 'cancel_search_manga_acc'}}, row_width=2)
