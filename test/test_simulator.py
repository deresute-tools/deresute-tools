from src import customlogger as logger
from src.logic.card import Card
from src.logic.grandlive import GrandLive
from src.logic.grandunit import GrandUnit
from src.logic.live import Live
from src.logic.unit import Unit
from src.simulator import Simulator
from src.static.song_difficulty import Difficulty

logger.print_debug()

unit = Unit.from_query("karen4 sae3 miho4 momoka4 nagi2", custom_pots=(0, 0, 0, 0, 10))

live = Live()
live.set_music(music_name="あいくるしい", difficulty=Difficulty.REGULAR)
live.set_unit(unit)
sim = Simulator(live)
assert sim.simulate(perfect_play=True, appeals=170901)[1] == 544321

unit = Unit.from_query("sae4 chieri4 rika4 arisu3 kako2 uzuki2", custom_pots=(0, 10, 0, 0, 10))

live = Live()
live.set_music(music_name="Trust me", difficulty=Difficulty.MPLUS)
live.set_unit(unit)
sim = Simulator(live)
assert sim.simulate(perfect_play=True, appeals=261917)[1] == 1958643

sae4 = Card.from_query("sae4", custom_pots=(2, 10, 0, 0, 10))
chieri4 = Card.from_query("chieri4", custom_pots=(0, 10, 9, 0, 10))
yoshino3 = Card.from_query("yoshino3", custom_pots=(8, 10, 0, 0, 10))
rika4 = Card.from_query("rika4", custom_pots=(8, 10, 0, 0, 10))
mio4 = Card.from_query("mio4", custom_pots=(0, 5, 0, 0, 10))
kaede2_guest = Card.from_query("kaede2", custom_pots=(10, 10, 10, 0, 5))
unit = Unit.from_list([sae4, chieri4, yoshino3, rika4, mio4, kaede2_guest])

live = Live()
live.set_music(music_name="印象", difficulty=Difficulty.MPLUS)
live.set_unit(unit)
sim = Simulator(live)
assert sim.simulate(times=100, appeals=270000)[1] == 1736810

unitA = Unit.from_query("kaede2 chieri4 kyoko4 rika4 rika4u")
unitB = Unit.from_query("sae4 kozue2 momoka3 frederica3 sachiko4")
unitC = Unit.from_query("atsumi2 anzu3 anzu3u miku4 miku3")
gu = GrandUnit(unitA, unitB, unitC)
live = GrandLive()
live.set_music(music_name="Starry-Go-Round", difficulty=Difficulty.PIANO)
live.set_unit(gu)
sim = Simulator(live)
assert sim.simulate(times=10, appeals=490781)[1] == 3424303

unit_lskaren_flick = Unit.from_query("nao4 kaede4 karen3 akira1 haru2 kaede1")
unit_lsasuka_flick = Unit.from_query("nao4 kaede4 asuka3 akira1 haru2 kaede1")
unit_lskaren_slide = Unit.from_query("nao4 kaede4 karen3 yukimi2 haru2 kaede1")
unit_lsasuka_slide = Unit.from_query("nao4 kaede4 asuka3 yukimi2 haru2 kaede1")
unit_comborin_slide_flick = Unit.from_query("nao4 rin2 yukimi2 akira1 haru2 kaede1")
unit_combokae1_slide_flick = Unit.from_query("nao4 kaede1 yukimi2 akira1 haru2 kaede1")
unit_combokae2_slide_flick = Unit.from_query("nao4 kaede2 yukimi2 akira1 haru2 kaede1")
guest_cool_ens = Card.from_query("nao4", custom_pots=(10, 10, 10, 5, 0))
unit_vis_res1 = Unit.from_query("sae4 chieri4 yoshino3 rika4 mio4 kaede2")
unit_vis_res2 = Unit.from_query("sae4 chieri4 arisu3 rika4 kako2 kaede2")
kaede2_guest = Card.from_query("kaede2", custom_pots=(10, 10, 10, 0, 5))

unit_list = [unit_lskaren_flick, unit_lsasuka_flick, unit_lskaren_slide, unit_lsasuka_slide, unit_comborin_slide_flick,
             unit_combokae1_slide_flick, unit_combokae2_slide_flick]
# unit_list = [unit_vis_res1, unit_vis_res2]
for unit in unit_list:
    unit.update_card(5, guest_cool_ens)

    live = Live()
    live.set_music(music_name="バベル", difficulty=Difficulty.MPLUS)
    live.set_unit(unit)
    sim = Simulator(live)
    print(unit)
    print(sim.simulate(times=10, support=110256))
