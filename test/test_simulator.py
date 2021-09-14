import os

from logic.card import Card
from logic.live import Live

os.environ["DEBUG_MODE"] = "1"
import customlogger as logger
from logic.grandlive import GrandLive
from logic.grandunit import GrandUnit
from logic.unit import Unit
from simulator import Simulator
from static.song_difficulty import Difficulty

logger.print_debug()

# sae4 = Card.from_query("sae4", custom_pots=(2, 10, 0, 0, 10))
# chieri4 = Card.from_query("chieri4", custom_pots=(0, 10, 9, 0, 10))
# yoshino3 = Card.from_query("yoshino3", custom_pots=(8, 10, 0, 0, 10))
# rika4 = Card.from_query("rika4", custom_pots=(8, 10, 0, 0, 10))
# mio4 = Card.from_query("mio4", custom_pots=(0, 5, 0, 0, 10))
# kaede2_guest = Card.from_query("kaede2", custom_pots=(10, 10, 10, 0, 5))
# unit = Unit.from_list([sae4, chieri4, yoshino3, rika4, mio4, kaede2_guest])
#
# live = Live()
# live.set_music(music_name="Starry-Go-Round", difficulty=Difficulty.MPLUS, event=False)
# live.set_unit(unit)
# sim = Simulator(live)
# sim.simulate(times=100, appeals=400000).perfect_score
#
# unitA = Unit.from_query("kaede2 chieri4 kyoko4 rika4 rika4u")
# unitB = Unit.from_query("sae4 kozue2 momoka3 frederica3 sachiko4")
# unitC = Unit.from_query("atsumi2 anzu3 anzu3u miku4 miku3")
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(music_name="Starry-Go-Round", difficulty=Difficulty.PIANO)
# live.set_unit(gu)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=490781).perfect_score == 3424303
#
# unit = Unit.from_query("nao4 yukimi2 haru2 mizuki4 rin2 ranko3", custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="in fact", difficulty=Difficulty.MPLUS)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=302495).perfect_score == 1366223
#
# unit = Unit.from_query("kaede5 syoko4 yui5 shin3 makino2 frederica5", custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="Absolute Nine", difficulty=Difficulty.REGULAR)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=208617).perfect_score == 776777
#
# unit = Unit.from_list([201002, 100990, 201004, 100989, 300762, 100256], custom_pots=(5, 10, 10, 0, 10))
# live = Live()
# live.set_music(score_id=409, difficulty=Difficulty.MPLUS)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, support=113290).perfect_score == 2537631
#
# unit = Unit.from_query("kaede5 rin5 riina5 yasuha1 nono4 karen4", custom_pots=(0, 0, 0, 0, 10))
# unit.get_card(5).li = 50
# live = Live()
# live.set_music(music_name="バベル", difficulty=Difficulty.MASTER)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=217911).perfect_score == 1412638

# unit = Unit.from_list([200946, 200058, 100076, 100396, 300530, 200294], custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="Trust me", difficulty=Difficulty.MASTER)
# live.set_unit(unit)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=277043, time_offset=120).score == 561672
#
# unit = Unit.from_list([200946, 200058, 100076, 100396, 300530, 200294], custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="Brand new!", difficulty=Difficulty.MASTER)
# live.set_unit(unit)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=277043, time_offset=110).score == 570342
#
# unit = Unit.from_list([200946, 200058, 100076, 100396, 300530, 200294], custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="Never ends", difficulty=Difficulty.MPLUS)
# live.set_unit(unit)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=277043, time_offset=400).score == 629870
#
# unit = Unit.from_list([200946, 200058, 100076, 100396, 300530, 200294], custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="Tulip", difficulty=Difficulty.MPLUS)
# live.set_unit(unit)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=277043, time_offset=113).score == 654967
#
# unitA = Unit.from_list([200946, 200496, 100396, 300572, 200058], custom_pots=(0, 0, 0, 0, 10))
# unitB = Unit.from_list([100936, 300078, 100500, 200378, 200072], custom_pots=(0, 0, 0, 0, 10))
# unitC = Unit.from_list([300600, 100076, 200644, 100506, 200892], custom_pots=(0, 0, 0, 0, 10))
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(music_name="M@GIC", difficulty=Difficulty.FORTE)
# live.set_unit(gu)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=444572, time_offset=120).score == 991859
#
# unitA = Unit.from_list([200946, 200496, 100396, 300572, 200058], custom_pots=(0, 0, 0, 0, 10))
# unitB = Unit.from_list([100936, 300078, 200620, 200378, 200072], custom_pots=(0, 0, 0, 0, 10))
# unitC = Unit.from_list([300600, 100076, 200644, 100506, 200892], custom_pots=(0, 0, 0, 0, 10))
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(music_name="M@GIC", difficulty=Difficulty.FORTE)
# live.set_unit(gu)
# sim = Simulator(live, special_offset=0.075)
# assert sim.simulate_auto(appeals=451228, time_offset=218, mirror=True).score == 936614
#
# unit = Unit.from_query("nao4 yukimi2 haru2 mizuki4 rin2 ranko3", custom_pots=(0, 0, 0, 0, 10))
# live = Live()
# live.set_music(music_name="あらかねの器", difficulty=Difficulty.MPLUS)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=302495).perfect_score == 1576804
# sim = Simulator(live, left_inclusive=True, right_inclusive=False)
# assert sim.simulate(perfect_play=True, appeals=302495).perfect_score == 1593970
# sim = Simulator(live, left_inclusive=True, right_inclusive=True)
# assert sim.simulate(perfect_play=True, appeals=302495).perfect_score == 1610415
# sim = Simulator(live, left_inclusive=False, right_inclusive=False)
# assert sim.simulate(perfect_play=True, appeals=302495).perfect_score == 1557771
#
# unit = Unit.from_list([100936, 100964, 100708, 100108, 100914], custom_pots=(10, 0, 0, 0, 0))
# live = Live()
# live.set_music(music_name="Just Us Justice", difficulty=Difficulty.MPLUS, event=True)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate_theoretical_max(appeals=350528).abuse_df['delta'].sum() == 54786
#
#
# sae4 = Card.from_query("sae4", custom_pots=(5,10,10,0,10))
# riina5 = Card.from_query("riina5", custom_pots=(5,10,10,0,10))
# riina5u = Card.from_query("riina5u", custom_pots=(5,10,10,0,10))
# hajime4 = Card.from_query("hajime4", custom_pots=(5,10,10,0,10))
# arisu3 = Card.from_query("arisu3", custom_pots=(5,10,10,0,10))
# yui2 = Card.from_query("yui2", custom_pots=(10,10,10,0,00))
# unit = Unit.from_list([sae4, riina5, riina5u, hajime4, arisu3, yui2], custom_pots=(5, 10, 10, 0, 10))
# live = Live()
# live.set_music(score_id=615, difficulty=Difficulty.MPLUS, event=True)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate_theoretical_max(support=113290).abuse_df['delta'].sum() == 76303
#
#
# unitA = Unit.from_list([300940, 300888, 300690, 300844, 300856])
# unitB = Unit.from_list([300798, 300830, 300716, 200894, 100928])
# unitC = Unit.from_list([300648, 300812, 300846, 300811, 300845])
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(music_name="Starry-Go-Round", difficulty=Difficulty.PIANO)
# live.set_unit(gu)
# sim = Simulator(live)
# assert sim.simulate_theoretical_max(appeals=480692).max_score == 6554894
#
# unit = Unit.from_list([100936, 100708, 100914, 100584, 100456, 100964], custom_pots=(10, 5, 0, 10, 10))
# live = Live()
# live.set_music(score_id=637, difficulty=Difficulty.MPLUS, event=True)
# live.set_unit(unit)
# sim = Simulator(live)
# assert sim.simulate_theoretical_max(appeals=243551).abuse_df['delta'].sum() == 47441

# unitA = Unit.from_list([201002, 100990, 100612, 100918, 300152], custom_pots=(10,10,10,10,10))
# unitB = Unit.from_list([200720, 200980, 100944, 100882, 300896], custom_pots=(10,10,10,10,10))
# unitC = Unit.from_list([200906, 201044, 200930, 100916, 300882], custom_pots=(10,10,10,10,10))
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(score_id=443, difficulty=Difficulty.FORTE)
# live.set_unit(gu)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True, appeals=402866).perfect_score == 4270963
#
# unitA = Unit.from_list([200844, 200740, 200620, 200843, 200730], custom_pots=(0, 10, 5, 10, 10))
# unitB = Unit.from_list([200986, 200916, 201002, 201022, 200992], custom_pots=(0, 10, 5, 10, 10))
# unitC = Unit.from_list([201030, 200978, 200810, 300896, 100882], custom_pots=(0, 10, 5, 10, 10))
# gu = GrandUnit(unitA, unitB, unitC)
# live = GrandLive()
# live.set_music(score_id=443, difficulty=Difficulty.FORTE)
# live.set_unit(gu)
# sim = Simulator(live)
# assert sim.simulate(perfect_play=True).perfect_score == 7015156

unitA = Unit.from_list([100944, 200980, 300922, 200979, 300921], custom_pots=(5, 10, 10, 0, 10))
unitB = Unit.from_list([300856, 201040, 300572, 100978, 100578], custom_pots=(5, 10, 10, 0, 10))
unitC = Unit.from_list([300940, 300830, 200894, 300829, 100798], custom_pots=(5, 10, 10, 0, 10))
gu = GrandUnit(unitA, unitB, unitC)
live = GrandLive()
live.set_music(score_id=419, difficulty=Difficulty.FORTE)
live.set_unit(gu)
sim = Simulator(live)
assert sim.simulate(times=10).perfect_score == 8939389
