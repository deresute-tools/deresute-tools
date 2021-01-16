from src import customlogger as logger
from src.logic.card import Card
from src.logic.grandlive import GrandLive
from src.logic.grandunit import GrandUnit
from src.logic.live import Live
from src.logic.unit import Unit
from src.simulator import Simulator
from src.static.song_difficulty import Difficulty

logger.print_debug()

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
assert sim.simulate(times=100, appeals=270000)[1] == 1738373

unitA = Unit.from_query("kaede2 chieri4 kyoko4 rika4 rika4u")
unitB = Unit.from_query("sae4 kozue2 momoka3 frederica3 sachiko4")
unitC = Unit.from_query("atsumi2 anzu3 anzu3u miku4 miku3")
gu = GrandUnit(unitA, unitB, unitC)
live = GrandLive()
live.set_music(music_name="Starry-Go-Round", difficulty=Difficulty.PIANO)
live.set_unit(gu)
sim = Simulator(live)
sim.simulate(times=10, appeals=490781)[1] == 3424303

unit = Unit.from_query("nao4 yukimi2 haru2 mizuki4 rin2 ranko3", custom_pots=(0, 0, 0, 0, 10))
live = Live()
live.set_music(music_name="in fact", difficulty=Difficulty.MPLUS)
live.set_unit(unit)
sim = Simulator(live)
assert sim.simulate(perfect_play=True, appeals=302495)[1] == 1318765

unit = Unit.from_query("kaede5 syoko4 yui5 shin3 makino2 frederica5", custom_pots=(0, 0, 0, 0, 10))
live = Live()
live.set_music(music_name="Absolute Nine", difficulty=Difficulty.REGULAR)
live.set_unit(unit)
sim = Simulator(live)
sim.simulate(perfect_play=True, appeals=208617)[1] == 745549
