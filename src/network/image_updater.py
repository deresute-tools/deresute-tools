import os
import time
import zipfile
from concurrent.futures.thread import ThreadPoolExecutor

import requests
from PIL import Image

import settings
from settings import IMAGE_PATH, IMAGE_PATH32, IMAGE_PATH64, ZIP_PATH
from src import customlogger as logger
from src.network.kirara_query import _base_query
from src.utils import storage


FORMAT = "https://hidamarirhodonite.kirara.ca/icon_card/{:06d}.png"


def update_image(card_id, sleep=0.1):
    path = IMAGE_PATH / "{:06d}.png".format(card_id)
    path32 = IMAGE_PATH32 / "{:06d}.jpg".format(card_id)
    path64 = IMAGE_PATH64 / "{:06d}.jpg".format(card_id)
    if not storage.exists(path):
        time.sleep(sleep)
        r = requests.get(FORMAT.format(card_id))
        if r.status_code == 200:
            with storage.get_writer(path, 'wb') as fwb:
                for chunk in r:
                    fwb.write(chunk)
    if not path64.exists() and not path32.exists():
        img = Image.open(str(path)).convert('RGB')
        if not path32.exists():
            img.resize((32, 32), Image.ANTIALIAS).save(str(path32), format='JPEG')
        if not path64.exists():
            img.resize((64, 64), Image.ANTIALIAS).save(str(path64), format='JPEG')


def update_all(sleep=0.1):
    _try_extract_cache()
    if not IMAGE_PATH64.exists():
        IMAGE_PATH64.mkdir()
    if not IMAGE_PATH32.exists():
        IMAGE_PATH32.mkdir()
    card_data = _base_query("list/card_t")['result']
    logger.debug("Getting icons for {} cards".format(len(card_data)))
    card_ids = [int(card['id']) for card in card_data]
    card_ids_plus = [_ + 1 for _ in card_ids]
    with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
        for card_id in card_ids + card_ids_plus:
            executor.submit(update_image, card_id, sleep)


def _try_extract_cache():
    if os.path.exists(ZIP_PATH):
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(IMAGE_PATH)
        # os.remove(ZIP_PATH)


update_all(0.1)
