from pathlib import Path

from src.scheduler.jobs.new_chapters.new_mg_chapters import get_new_manga_chapters
from src.database import TrackedManga, MangaAccounts, TelegramAccounts
from loader import Session_db, bot, scheduler
from src.logger.base_logger import log

from requests import get
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, DBAPIError
from telebot.apihelper import ApiException


@scheduler.scheduled_job('interval', minutes=5)
def send_notif_new_chapters() -> None:
    log.info('Старт джобы на отправку уведомлений о выходе новых глав')
    log.debug(f'{__name__}')
    releases = get_new_manga_chapters()

    for release in releases:
        # Получение телеграмм аккаунта и id обложки манги
        send_data = _get_send_data(release.slug)
        cover = _get_cover_data(release.slug, send_data[0].get('cover_id'))
        for data in send_data:
            for chapter in release.chapters:
                _send_release_in_tg(release.name, chapter.volume, chapter.number, chapter.url, cover,
                                    data.get('account_id'))


def _get_send_data(manga_slug: str) -> list[dict]:
    log.debug(f'{__name__}, manga_slug={manga_slug} (Получение телеграмм аккаунтов и id обложки манги из ДБ)')
    with Session_db() as session:
        try:
            stmt = select(TelegramAccounts.account_id, TrackedManga.cover_id).join(
                MangaAccounts.readable_manga).join(MangaAccounts.telegram_accounts).where(
                TrackedManga.slug == manga_slug)
            result_sql = session.execute(stmt).mappings().all()

            log.debug(f'Запрос = {stmt}')
        except (SQLAlchemyError, DBAPIError) as error:
            log.error('Ошибка при получении телеграмм аккаунтов и id обложки манги из ДБ (SQLAlchemy)', exc_info=error)
            raise
        except Exception as error:
            log.error('Ошибка при получении телеграмм аккаунтов и id обложки манги из ДБ', exc_info=error)
            raise

    log.debug(f'Список телеграмм аккаунтов и id обложки result_sql={result_sql}')
    return result_sql


def _get_cover_data(manga_slug: str, send_data: str) -> bytes:
    log.debug(f'{__name__} получение обложки манги manga_slug={manga_slug}, send_data={send_data}')

    try:
        response = get(f'https://cover.imglib.info/uploads/cover/{manga_slug}/cover/{send_data[0][1]}_250x350.jpg')
    except (HTTPError, ConnectionError, Timeout, RequestException) as error:
        log.error('Ошибка при получении обложки манги (requests)', exc_info=error)
        return _get_placeholder_cover()
    except Exception as error:
        log.error('Ошибка при получении обложки манги', exc_info=error)
        return _get_placeholder_cover()

    result = response.content
    log.debug(f'Обложка манги={result}')
    return result


def _get_placeholder_cover() -> bytes:
    log.debug(f'{__name__}(получение заглушки обложки манга)')
    placeholder_path = Path.joinpath(Path.cwd(), r'.\data\images\placeholder_cover.png')
    with open(placeholder_path, 'rb') as fr:
        return fr.read()


def _send_release_in_tg(manga_name: str, chap_vol: int, chap_num: float, chap_url: str, cover: bytes,
                        tg_id: int) -> None:
    try:
        bot.send_photo(tg_id, photo=cover, caption=f'{manga_name}\nТом {chap_vol} глава '
                                                   f'{int(chap_num) if chap_num % 1 == 0 else chap_num}\n\n{chap_url}')
    except ApiException as error:
        log.error('Ошибка при отправке фотографии через telebot', exc_info=error)
    except Exception as error:
        log.error('Ошибка при отправке фотографии', exc_info=error)