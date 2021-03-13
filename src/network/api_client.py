import os
import subprocess
from ast import literal_eval

import customlogger as logger
from logic.card import Card
from settings import TOOL_EXE, TEMP_PATH


def remove_temp(f):
    def decorate(*args, **kwargs):
        res = f(*args, **kwargs)
        if not os.path.exists(TEMP_PATH):
            logger.info("Failed to run CGSS API")
        else:
            os.remove(TEMP_PATH)
        return res

    return decorate


@remove_temp
def get_cards(game_id):
    subprocess.call(list(map(str, [TOOL_EXE, "card", game_id, TEMP_PATH])))
    if not os.path.exists(TEMP_PATH):
        return
    with open(TEMP_PATH) as fr:
        cards = fr.read().strip().split(",")
        return cards


@remove_temp
def get_top_build(live_detail_id):
    subprocess.call(list(map(str, [TOOL_EXE, "build", live_detail_id, TEMP_PATH])))
    if not os.path.exists(TEMP_PATH):
        return
    with open(TEMP_PATH) as fr:
        build = literal_eval(fr.read())
        support = build['backmember_appeal']
        cards = [
            Card.from_id(_['card_id'], custom_pots=(
                _['potential_param_1'],
                _['potential_param_2'],
                _['potential_param_3'],
                _['potential_param_4'],
                _['potential_param_5']
            ))
            for _ in build['member_list']
        ]
        if len(build['supporter']) > 0:
            cards.append(
                Card.from_id(build['supporter']['card_id'], custom_pots=(
                    build['supporter']['potential_param_1'],
                    build['supporter']['potential_param_2'],
                    build['supporter']['potential_param_3'],
                    build['supporter']['potential_param_4'],
                    build['supporter']['potential_param_5']
                ))
            )
        return cards, support
